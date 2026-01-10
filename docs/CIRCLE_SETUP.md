# Circle Developer Account Setup

## Required Accounts & API Keys

### 1. Circle Developer Account

1. Visit [Circle Developer Portal](https://developers.circle.com)
2. Sign up / Log in
3. Create a new application
4. Note your **App ID** (for Circle Wallets)

### 2. Circle Gateway API

1. In Circle Developer Portal, navigate to **Gateway**
2. Generate API key for Gateway micropayments
3. Set `CIRCLE_GATEWAY_API_KEY` in backend `.env`

### 3. Circle Wallets API

1. In Circle Developer Portal, navigate to **Wallets**
2. Generate API key for wallet management
3. Set `CIRCLE_WALLETS_API_KEY` in backend `.env`
4. Set `NEXT_PUBLIC_CIRCLE_APP_ID` in frontend `.env`

### 4. Google AI / Gemini API

1. Visit [Google AI Studio](https://aistudio.google.com)
2. Create API key
3. Set `GOOGLE_AI_API_KEY` in backend `.env`

### 5. Arc Testnet

- **RPC URL**: `https://arc-testnet.rpc.circle.com`
- **Chain ID**: `11124`
- **USDC Address**: (To be confirmed - check Circle docs)
- **Faucet**: (Check Circle docs for testnet USDC)

## Environment Variables Checklist

### Backend `.env`
- [ ] `DATABASE_URL`
- [ ] `CIRCLE_GATEWAY_API_KEY`
- [ ] `CIRCLE_WALLETS_API_KEY`
- [ ] `GOOGLE_AI_API_KEY`
- [ ] `ARC_RPC_URL`
- [ ] `USDC_ADDRESS` (Arc testnet)
- [ ] `AGENT_WALLET_ADDRESS`
- [ ] `AGENT_WALLET_PRIVATE_KEY`
- [ ] `INSURER_WALLET_ADDRESS`
- [ ] `INSURER_WALLET_PRIVATE_KEY`

### Frontend `.env.local`
- [ ] `NEXT_PUBLIC_API_URL`
- [ ] `NEXT_PUBLIC_ARC_RPC_URL`
- [ ] `NEXT_PUBLIC_ARC_CHAIN_ID`
- [ ] `NEXT_PUBLIC_CLAIM_ESCROW_CONTRACT_ADDRESS`
- [ ] `NEXT_PUBLIC_CIRCLE_APP_ID`

## Wallet Setup

### Agent Wallet
- Receives micropayments from x402 verifiers
- Can be created via Circle Wallets API
- Store address and private key securely

### Insurer Wallet
- Triggers claim settlement
- Can be created via Circle Wallets API
- Store address and private key securely

## Testing

1. Deploy `ClaimEscrow` contract to Arc testnet
2. Get testnet USDC from faucet
3. Test Gateway micropayments with small amounts
4. Verify Circle Wallets integration
