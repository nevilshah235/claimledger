// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ClaimEscrow
 * @notice Minimal escrow contract for insurance claim settlements on Arc
 * @dev Holds USDC in escrow and releases funds when claim is approved
 * Uses USDC as native gas token on Arc
 */
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract ClaimEscrow {
    // USDC contract address on Arc (to be set on deployment)
    IERC20 public usdc;
    
    // Claim escrow balances
    mapping(uint256 => uint256) public escrowBalances;
    
    // Claim settlement records
    mapping(uint256 => bool) public settledClaims;
    
    // Events
    event EscrowDeposited(uint256 indexed claimId, address indexed depositor, uint256 amount);
    event ClaimSettled(uint256 indexed claimId, address indexed recipient, uint256 amount);
    
    /**
     * @notice Constructor sets USDC contract address
     * @param _usdcAddress USDC contract address on Arc
     */
    constructor(address _usdcAddress) {
        usdc = IERC20(_usdcAddress);
    }
    
    /**
     * @notice Deposit USDC into escrow for a claim
     * @param claimId Unique claim identifier
     * @param amount Amount of USDC to escrow (in USDC units, 6 decimals)
     */
    function depositEscrow(uint256 claimId, uint256 amount) external {
        require(amount > 0, "Amount must be greater than 0");
        require(!settledClaims[claimId], "Claim already settled");
        
        // Transfer USDC from caller to this contract
        require(
            usdc.transferFrom(msg.sender, address(this), amount),
            "USDC transfer failed"
        );
        
        escrowBalances[claimId] += amount;
        
        emit EscrowDeposited(claimId, msg.sender, amount);
    }
    
    /**
     * @notice Approve and settle a claim by transferring USDC to recipient
     * @param claimId Unique claim identifier
     * @param amount Amount of USDC to transfer (in USDC units, 6 decimals)
     * @param recipient Address to receive the USDC
     */
    function approveClaim(
        uint256 claimId,
        uint256 amount,
        address recipient
    ) external {
        require(amount > 0, "Amount must be greater than 0");
        require(recipient != address(0), "Invalid recipient address");
        require(!settledClaims[claimId], "Claim already settled");
        require(escrowBalances[claimId] >= amount, "Insufficient escrow balance");
        
        // Mark claim as settled
        settledClaims[claimId] = true;
        
        // Transfer USDC to recipient
        require(
            usdc.transfer(recipient, amount),
            "USDC transfer failed"
        );
        
        // Update escrow balance
        escrowBalances[claimId] -= amount;
        
        emit ClaimSettled(claimId, recipient, amount);
    }
    
    /**
     * @notice Get escrow balance for a claim
     * @param claimId Unique claim identifier
     * @return balance Current escrow balance in USDC
     */
    function getEscrowBalance(uint256 claimId) external view returns (uint256) {
        return escrowBalances[claimId];
    }
    
    /**
     * @notice Check if a claim has been settled
     * @param claimId Unique claim identifier
     * @return settled True if claim has been settled
     */
    function isSettled(uint256 claimId) external view returns (bool) {
        return settledClaims[claimId];
    }
}
