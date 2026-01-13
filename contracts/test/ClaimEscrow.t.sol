// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {ClaimEscrow} from "../src/ClaimEscrow.sol";

// Mock USDC contract for testing
contract MockUSDC {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Insufficient balance");
        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        allowance[from][msg.sender] -= amount;
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
    
    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }
}

contract ClaimEscrowTest is Test {
    ClaimEscrow public escrow;
    MockUSDC public usdc;
    
    address public claimant = address(0x1);
    address public insurer = address(0x2);
    address public recipient = address(0x3);
    
    uint256 public constant CLAIM_ID = 1;
    uint256 public constant ESCROW_AMOUNT = 1000 * 1e6; // 1000 USDC (6 decimals)
    uint256 public constant SETTLEMENT_AMOUNT = 950 * 1e6; // 950 USDC
    
    function setUp() public {
        usdc = new MockUSDC();
        escrow = new ClaimEscrow(address(usdc));
        
        // Mint USDC to claimant
        usdc.mint(claimant, ESCROW_AMOUNT);
        vm.prank(claimant);
        usdc.approve(address(escrow), ESCROW_AMOUNT);
    }
    
    function testDepositEscrow() public {
        vm.prank(claimant);
        escrow.depositEscrow(CLAIM_ID, ESCROW_AMOUNT);
        
        assertEq(escrow.getEscrowBalance(CLAIM_ID), ESCROW_AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), ESCROW_AMOUNT);
    }
    
    function testApproveClaim() public {
        // Deposit escrow
        vm.prank(claimant);
        escrow.depositEscrow(CLAIM_ID, ESCROW_AMOUNT);
        
        // Approve and settle
        escrow.approveClaim(CLAIM_ID, SETTLEMENT_AMOUNT, recipient);
        
        assertTrue(escrow.isSettled(CLAIM_ID));
        assertEq(usdc.balanceOf(recipient), SETTLEMENT_AMOUNT);
        assertEq(escrow.getEscrowBalance(CLAIM_ID), ESCROW_AMOUNT - SETTLEMENT_AMOUNT);
    }
    
    function testCannotSettleTwice() public {
        vm.prank(claimant);
        escrow.depositEscrow(CLAIM_ID, ESCROW_AMOUNT);
        
        escrow.approveClaim(CLAIM_ID, SETTLEMENT_AMOUNT, recipient);
        
        // Try to settle again
        vm.expectRevert("Claim already settled");
        escrow.approveClaim(CLAIM_ID, SETTLEMENT_AMOUNT, recipient);
    }
    
    function testCannotSettleMoreThanEscrow() public {
        vm.prank(claimant);
        escrow.depositEscrow(CLAIM_ID, ESCROW_AMOUNT);
        
        uint256 excessAmount = ESCROW_AMOUNT + 1;
        vm.expectRevert("Insufficient escrow balance");
        escrow.approveClaim(CLAIM_ID, excessAmount, recipient);
    }
}
