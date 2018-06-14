import pytest
# KTXXX - do we need this?
from plasma.utils.utils import pack_utxo_pos
from plasma.child_chain.exceptions import (InvalidBlockSignatureException,
                                           InvalidTxSignatureException,
                                           TxAlreadySpentException)


def test_apply_deposit(test_lang):
    owner = test_lang.get_account()

    test_lang.deposit(owner, 100)

    deposit_block_number = 1
    # import pdb; pdb.set_trace()
    deposit_block = test_lang.child_chain.blocks[deposit_block_number]
    assert len(deposit_block.transaction_set) == 1


def test_send_tx_with_sig(test_lang):
    owner_1 = test_lang.get_account()
    owner_2 = test_lang.get_account()

    deposit_id = test_lang.deposit(owner_1, 100)
    test_lang.transfer(deposit_id, 0, owner_2, 100, owner_1)


def test_send_tx_no_sig(test_lang):
    owner_1 = test_lang.get_account()
    owner_2 = test_lang.get_account()
    key = None

    deposit_id = test_lang.deposit(owner_1, 100)

    with pytest.raises(InvalidTxSignatureException):
        test_lang.transfer(deposit_id, 0, owner_2, 100, key)


def test_send_tx_invalid_sig(test_lang):
    owner_1 = test_lang.get_account()
    owner_2 = test_lang.get_account()
    owner_3 = test_lang.get_account()

    deposit_id = test_lang.deposit(owner_1, 100)

    with pytest.raises(InvalidTxSignatureException):
        test_lang.transfer(deposit_id, 0, owner_2, 100, owner_3)


def test_send_tx_double_spend(test_lang):
    owner_1 = test_lang.get_account()
    owner_2 = test_lang.get_account()

    deposit_id = test_lang.deposit(owner_1, 100)
    test_lang.transfer(deposit_id, 0, owner_2, 100, owner_1)

    with pytest.raises(TxAlreadySpentException):
        test_lang.transfer(deposit_id, 0, owner_2, 100, owner_1)


def test_submit_block(test_lang):
    old_block_number = test_lang.child_chain.current_block_number
    test_lang.submit_block()
    assert test_lang.child_chain.current_block_number == old_block_number + test_lang.child_chain.child_block_interval


def test_submit_block_no_sig(test_lang):
    with pytest.raises(InvalidBlockSignatureException):
        test_lang.submit_block(None)


def test_submit_block_invalid_sig(test_lang):
    owner_1 = test_lang.get_account()

    with pytest.raises(InvalidBlockSignatureException):
        test_lang.submit_block(owner_1)


# def apply_exit(self, event):
#     event_args = event['args']
#
#     utxo_pos = event_args['utxoPos']
#
#     self.mark_utxo_spent(*unpack_utxo_pos(utxo_pos))


# def test_apply_exit(child_chain):
#     owner_1 = test_lang.get_account()
#     owner_2 = test_lang.get_account()
#
#     deposit_id = test_lang.deposit(owner_1, 100)
#     transfer_id = test_lang.transfer(deposit_id, 0, owner_2, 100, owner_1)
#     test_lang.submit_block()
#     test_lang.confirm(transfer_id, owner_1)
#     test_lang.withdraw(transfer_id, 0, owner_2)
#
#     (blknum, txindex, oindex) = (1, 0, 0)
#     sample_event = {
#         'args': {
#             'exitor': '0xfd02EcEE62797e75D86BCff1642EB0844afB28c7',
#             'utxoPos': pack_utxo_pos(blknum, txindex, oindex),
#             'amount': 100,
#         },
#         'event': 'ExitStarted',
#         'logIndex': 0,
#         'transactionIndex': 0,
#         'transactionHash': '0x35e6446818b53b2c4537ebba32b9453b274286ffbb25e5b521a6b0a33e2cb953',
#         'address': '0xA3B2a1804203b75b494028966C0f62e677447A39',
#         'blockHash': '0x2550290dd333ea2876539b7ba474a804a9143b0d4ecb57b9d824f07ffd016747',
#         'blockNumber': 1
#     }
#     child_chain.apply_exit(sample_event)
#
#     # Transaction now marked spent
#     assert child_chain.blocks[0].transaction_set[0].spent1
