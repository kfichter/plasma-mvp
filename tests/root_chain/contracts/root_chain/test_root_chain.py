import pytest
import rlp
from ethereum.tools import tester
from plasma.child_chain.transaction import Transaction, UnsignedTransaction
from plasma.utils.merkle.fixed_merkle import FixedMerkle
from plasma.utils.utils import get_merkle_of_leaves, confirm_tx

null_address = b'\x00' * 20
null_sigs = b'\x00' * 130
value_1 = 100
value_2 = value_1 * 2
owner, key = tester.a1, tester.k1
authority_key = tester.k0
empty_block = FixedMerkle(16, [], True).root

@pytest.fixture
def root_chain(t, get_contract):
    contract = get_contract('RootChain/RootChain.sol')
    t.chain.mine()
    return contract

@pytest.fixture
def deposit_tx():
    return Transaction(0, 0, 0, 0, 0, 0, owner, value_1, null_address, 0, 0)

def to_hex_address(address):
    return '0x' + address.hex()

def test_next_block_should_round_to_next_1000(root_chain):
    assert root_chain.nextWeekOldChildBlock(0) == 1000

def test_deposit_with_valid_value_should_succeed(t, root_chain, deposit_tx):
    tx_bytes = rlp.encode(deposit_tx, UnsignedTransaction)
    blknum = root_chain.getDepositBlock()

    # Submit with the correct value
    root_chain.deposit(tx_bytes, value=value_1)

    # Assert that the block was created correctly
    deposit_block = root_chain.getChildChain(blknum)
    root = get_merkle_of_leaves(16, [deposit_tx.hash + deposit_tx.sig1 + deposit_tx.sig2]).root
    timestamp = t.chain.head_state.timestamp
    assert deposit_block == [root, timestamp]

def test_deposit_with_invalid_value_should_fail(root_chain, deposit_tx):
    tx_bytes = rlp.encode(deposit_tx, UnsignedTransaction)
    blknum = root_chain.getDepositBlock()
    
    # Submit with an invalid value
    with pytest.raises(tester.TransactionFailed):
        root_chain.deposit(tx_bytes, value=value_2)

    # Assert that the block was not created
    deposit_block = root_chain.getChildChain(blknum)
    assert deposit_block == [b'\x00' * 32, 0]

def test_start_exit_from_deposit_should_succeed(root_chain, deposit_tx):
    tx_bytes = rlp.encode(deposit_tx, UnsignedTransaction)
    dep_blknum = root_chain.getDepositBlock()
    root_chain.deposit(tx_bytes, value=value_1)

    # Calculate the UTXO position
    utxoPos = dep_blknum * 1000000000

    # Create a membership proof 
    merkle = FixedMerkle(16, [deposit_tx.merkle_hash], True)
    proof = merkle.create_membership_proof(deposit_tx.merkle_hash)

    # Combine signatures
    sigs = deposit_tx.sig1 + deposit_tx.sig2

    # Start the exit
    root_chain.startExit(utxoPos, tx_bytes, proof, sigs,
                         '', '', '',
                         '', '', '',
                         sender=key)

    # Assert that the exit was inserted correctly
    assert root_chain.exits(utxoPos) == [to_hex_address(owner), value_1, utxoPos]

def test_start_exit_from_valid_single_input_tx_should_succeed(root_chain, deposit_tx):
    deposit_tx_bytes = rlp.encode(deposit_tx, UnsignedTransaction)

    # Create a valid input
    root_chain.deposit(deposit_tx_bytes, value=value_1)

    # Create a membership proof for that transaction
    merkle = FixedMerkle(16, [deposit_tx.merkle_hash], True)
    proof = merkle.create_membership_proof(deposit_tx.merkle_hash)

    # Submit two empty blocks
    root_chain.submitBlock(empty_block, sender=authority_key)
    root_chain.submitBlock(empty_block, sender=authority_key)

    # Create a transaction spending the input
    tx = Transaction(1, 0, 0, 0, 0, 0, owner, value_1, null_address, 0, 0)
    tx.sign1(key)
    
    blknum = root_chain.currentChildBlock()
    merkle1 = FixedMerkle(16, [tx.merkle_hash], True)
    root_chain.submitBlock(merkle1.root, sender=authority_key)

    # Calculate the UTXO position
    utxoPos = blknum * 1000000000

    # Create a membership proof 
    proof1 = merkle1.create_membership_proof(tx.merkle_hash)

    # Combine signatures
    sigs = tx.sig1 + tx.sig2

    # Start the exit
    tx_bytes = rlp.encode(tx, UnsignedTransaction)
    root_chain.startExit(utxoPos, tx_bytes, proof1, sigs,
                         deposit_tx_bytes, proof, null_sigs,
                         '', '', '',
                         sender=key)

    # Assert that the exit was inserted correctly
    assert root_chain.exits(utxoPos) == [to_hex_address(owner), value_1, utxoPos]

def test_start_exit_from_invalid_single_input_tx_should_fail(root_chain, deposit_tx):
    deposit_tx_bytes = rlp.encode(deposit_tx, UnsignedTransaction)

    # Create a valid input
    root_chain.deposit(deposit_tx_bytes, value=value_1)

    # Create a membership proof for that transaction
    merkle = FixedMerkle(16, [deposit_tx.merkle_hash], True)
    proof = merkle.create_membership_proof(deposit_tx.merkle_hash)

    # Create a transaction spending the input before waiting that the input is 3 blocks old
    tx = Transaction(1, 0, 0, 0, 0, 0, owner, value_1, null_address, 0, 0)
    tx.sign1(key)
    
    blknum = root_chain.currentChildBlock()
    merkle1 = FixedMerkle(16, [tx.merkle_hash], True)
    root_chain.submitBlock(merkle1.root, sender=authority_key)

    # Calculate the UTXO position
    utxoPos = blknum * 1000000000

    # Create a membership proof 
    proof1 = merkle1.create_membership_proof(tx.merkle_hash)

    # Combine signatures
    sigs = tx.sig1 + tx.sig2

    # Start the exit
    tx_bytes = rlp.encode(tx, UnsignedTransaction)
    with pytest.raises(tester.TransactionFailed):
        root_chain.startExit(utxoPos, tx_bytes, proof1, sigs,
                            deposit_tx_bytes, proof, null_sigs,
                            '', '', '',
                            sender=key)

    # Assert that the exit was not inserted
    assert root_chain.exits(utxoPos) == [to_hex_address(null_address), 0, 0]

def test_start_exit_from_valid_double_input_tx_should_succeed(root_chain, deposit_tx):
    deposit_tx_bytes = rlp.encode(deposit_tx, UnsignedTransaction)

    # Create two valid inputs
    root_chain.deposit(deposit_tx_bytes, value=value_1)
    root_chain.deposit(deposit_tx_bytes, value=value_1)

    # Create a membership proof (same for both)
    merkle = FixedMerkle(16, [deposit_tx.merkle_hash], True)
    proof = merkle.create_membership_proof(deposit_tx.merkle_hash)

    # Submit two empty blocks
    root_chain.submitBlock(empty_block, sender=authority_key)
    root_chain.submitBlock(empty_block, sender=authority_key)

    # Create a transaction spending the inputs
    tx = Transaction(1, 0, 0, 2, 0, 0, owner, value_2, null_address, 0, 0)
    tx.sign1(key)
    tx.sign2(key)

    blknum = root_chain.currentChildBlock()
    merkle1 = FixedMerkle(16, [tx.merkle_hash], True)
    root_chain.submitBlock(merkle1.root, sender=authority_key)

    # Calculate the UTXO position
    utxoPos = blknum * 1000000000

    # Create a membership proof 
    proof1 = merkle1.create_membership_proof(tx.merkle_hash)

    # Combine signatures
    sigs = tx.sig1 + tx.sig2

    # Start the exit
    tx_bytes = rlp.encode(tx, UnsignedTransaction)
    root_chain.startExit(utxoPos, tx_bytes, proof1, sigs,
                         deposit_tx_bytes, proof, null_sigs,
                         deposit_tx_bytes, proof, null_sigs,
                         sender=key)

    # Assert that the exit was inserted correctly
    assert root_chain.exits(utxoPos) == [to_hex_address(owner), value_2, utxoPos]

'''
def test_challenge_exit(t, u, root_chain):
    owner, value_1, key = t.a1, 100, t.k1
    null_address = b'\x00' * 20
    tx1 = Transaction(0, 0, 0, 0, 0, 0,
                      owner, value_1, null_address, 0, 0)
    tx_bytes1 = rlp.encode(tx1, UnsignedTransaction)
    dep1_blknum = root_chain.getDepositBlock()
    root_chain.deposit(tx_bytes1, value=value_1)
    merkle = FixedMerkle(16, [tx1.merkle_hash], True)
    proof = merkle.create_membership_proof(tx1.merkle_hash)
    confirmSig1 = confirm_tx(tx1, root_chain.getChildChain(dep1_blknum)[0], key)
    sigs = tx1.sig1 + tx1.sig2 + confirmSig1
    exitId1 = dep1_blknum * 1000000000 + 10000 * 0 + 0
    root_chain.startExit(exitId1, tx_bytes1, proof, sigs, sender=key)
    tx2 = Transaction(dep1_blknum, 0, 0, 0, 0, 0,
                      owner, value_1, null_address, 0, 0)
    tx2.sign1(key)
    tx_bytes2 = rlp.encode(tx2, UnsignedTransaction)
    merkle = FixedMerkle(16, [tx2.merkle_hash], True)
    proof = merkle.create_membership_proof(tx2.merkle_hash)
    child_blknum = root_chain.currentChildBlock()
    root_chain.submitBlock(merkle.root)
    confirmSig = confirm_tx(tx2, root_chain.getChildChain(child_blknum)[0], key)
    sigs = tx2.sig1 + tx2.sig2
    exitId2 = child_blknum * 1000000000 + 10000 * 0 + 0
    assert root_chain.exits(exitId1) == ['0x' + owner.hex(), 100, exitId1]
    assert root_chain.exitIds(exitId1) == exitId1
    root_chain.challengeExit(exitId2, exitId1, tx_bytes2, proof, sigs, confirmSig)
    assert root_chain.exits(exitId1) == ['0x0000000000000000000000000000000000000000', 0, 0]
    assert root_chain.exitIds(exitId1) == 0


def test_finalize_exits(t, u, root_chain):
    two_weeks = 60 * 60 * 24 * 14
    owner, value_1, key = t.a1, 100, t.k1
    null_address = b'\x00' * 20
    tx1 = Transaction(0, 0, 0, 0, 0, 0,
                      owner, value_1, null_address, 0, 0)
    tx_bytes1 = rlp.encode(tx1, UnsignedTransaction)
    dep1_blknum = root_chain.getDepositBlock()
    root_chain.deposit(tx_bytes1, value=value_1)
    merkle = FixedMerkle(16, [tx1.merkle_hash], True)
    proof = merkle.create_membership_proof(tx1.merkle_hash)
    confirmSig1 = confirm_tx(tx1, root_chain.getChildChain(dep1_blknum)[0], key)
    sigs = tx1.sig1 + tx1.sig2 + confirmSig1
    exitId1 = dep1_blknum * 1000000000 + 10000 * 0 + 0
    root_chain.startExit(exitId1, tx_bytes1, proof, sigs, sender=key)
    t.chain.head_state.timestamp += two_weeks * 2
    assert root_chain.exits(exitId1) == ['0x' + owner.hex(), 100, exitId1]
    assert root_chain.exitIds(exitId1) == exitId1
    pre_balance = t.chain.head_state.get_balance(owner)
    root_chain.finalizeExits(sender=t.k2)
    post_balance = t.chain.head_state.get_balance(owner)
    assert post_balance == pre_balance + value_1
    assert root_chain.exits(exitId1) == ['0x0000000000000000000000000000000000000000', 0, 0]
    assert root_chain.exitIds(exitId1) == 0
'''
