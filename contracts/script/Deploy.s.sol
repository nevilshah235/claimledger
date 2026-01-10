// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {ClaimEscrow} from "../src/ClaimEscrow.sol";

/**
 * @title DeployClaimEscrow
 * @notice Deployment script for ClaimEscrow contract on Arc
 * @dev Set USDC_ADDRESS environment variable before running
 */
contract DeployClaimEscrow is Script {
    function run() external {
        // USDC address on Arc testnet
        // TODO: Set actual USDC testnet address
        address usdcAddress = vm.envAddress("USDC_ADDRESS");
        
        vm.startBroadcast();
        
        ClaimEscrow escrow = new ClaimEscrow(usdcAddress);
        
        console.log("ClaimEscrow deployed at:", address(escrow));
        console.log("USDC address:", usdcAddress);
        
        vm.stopBroadcast();
    }
}
