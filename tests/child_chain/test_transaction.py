from plasma.child_chain.transaction import Transaction


def test_transaction(t, u, assert_failed):
    blknum1, txindex1, oindex1 = 1, 1, 0
    blknum2, txindex2, oindex2 = 2, 2, 1
    newowner1, amount1 = t.a1, 100
    newowner2, amount2 = t.a2, 150
    fee = 5
    oldowner1, oldowner2 = t.a1, t.a2
    key1, key2 = t.k1, t.k2
    tx = Transaction(blknum1, txindex1, oindex1,
                     blknum2, txindex2, oindex2,
                     newowner1, amount1,
                     newowner2, amount2,
                     fee)

    assert tx.to_dict() == {
        'blknum1': blknum1,
        'txindex1': txindex1,
        'oindex1': oindex1,
        'blknum2': blknum2,
        'txindex2': txindex2,
        'oindex2': oindex2,
        'newowner1': newowner1,
        'amount1': amount1,
        'newowner2': newowner2,
        'amount2': amount2,
        'fee': fee,
        'sig1': b'\x00' * 65,
        'sig2': b'\x00' * 65
    }

    tx.sign1(key1)
    tx.sign2(key2)

    assert tx.sender1 == oldowner1
    assert tx.sender2 == oldowner2
