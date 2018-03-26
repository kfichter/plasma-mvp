pragma solidity ^0.4.18;

import "./ByteUtils.sol";
import "./ECRecovery.sol";

/**
 * @title Validate
 * @dev <DESC>
 */

library Validate {
    function checkSigs(bytes32 txHash, uint256 blknum1, uint256 blknum2, bytes sigs)
        internal
        view
        returns (bool)
    {
        require(sigs.length % 65 == 0 && sigs.length <= 260);
        bytes memory sig1 = ByteUtils.slice(sigs, 0, 65);
        bytes memory sig2 = ByteUtils.slice(sigs, 65, 65);

        bool check1 = true;
        bool check2 = true;
        if (blknum1 > 0) {
            check1 = ECRecovery.recover(txHash, sig1) == msg.sender;
        } 
        if (blknum2 > 0) {
            check2 = ECRecovery.recover(txHash, sig2) == msg.sender;
        }
        return check1 && check2;
    }
}
