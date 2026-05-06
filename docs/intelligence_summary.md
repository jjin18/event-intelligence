# Eventful Summary

_Generated 2026-05-06T04:24:40.610344+00:00_

## 1. Organizer intent → structured objective
- **Event type:** hackathon
- **Who we want:** good hackers with great involvement in the community, experience working at Meta
- **Overall goal:** bring together a small group of skilled crypto hackers to build or compete collaboratively
- **City:** 
- **Target size:** 5
- **Success metrics:**
  - 5 RSVPs
  - 3-3 actual attendees
  - 20+ high-fit attendees aligned with the theme
  - 10 meaningful post-event follow-ups

## 2. Target Audience (ICP)
- **meta_crypto_engineer** (weight 10): A software engineer with direct Meta/Facebook experience who has since pivoted into crypto protocol or dApp development.
- **protocol_hacker** (weight 9): A hands-on builder who has shipped or contributed to a crypto protocol, L1/L2, or DeFi primitive with verifiable open-source work.
- **crypto_open_source_contributor** (weight 8): An active GitHub contributor to well-known crypto repositories with a track record of PRs merged into major ecosystems.
- **zk_specialist** (weight 8): A developer deeply focused on zero-knowledge cryptography, building circuits, proving systems, or zkEVM components.
- **community_lead_hacker** (weight 7): A well-connected individual who organizes or co-organizes crypto developer communities, ETHGlobal events, or protocol DAOs while remaining a practicing builder.
- **defi_smart_contract_dev** (weight 7): A battle-tested smart contract developer who has deployed and audited DeFi protocols handling real funds.
- **crypto_infra_engineer** (weight 6): An engineer specializing in blockchain infrastructure — nodes, indexers, RPC layers, or cross-chain bridges — with a systems programming background.
- **hackathon_veteran_winner** (weight 6): A repeat hackathon participant with demonstrated prize wins or notable project launches originating from hack events.

## 3. Avoid Personas
- **non_technical_crypto_marketer** (penalty 20): Community managers or marketers with no coding background dilute the builder-to-builder dynamic of a 5-person technical hackathon.
- **investor_or_vc** (penalty 18): VCs or angels attending to scout rather than build reduce hacking output and shift room dynamics away from collaboration.
- **blockchain_buzzword_generalist** (penalty 15): Individuals who claim broad crypto knowledge but lack verifiable technical output or specific protocol depth will slow a high-skill small group.
- **purely_web2_engineer** (penalty 12): Skilled engineers with no crypto exposure would require onboarding time that is incompatible with a focused small-group crypto hackathon.
- **nft_trader_hobbyist** (penalty 10): NFT collectors or traders without engineering skills add no technical value and misunderstand the collaborative build format.

## 4. Sourcing Strategy
### queries
- AI agent founders building production agent systems
- AI infra / devtools engineers shipping agent frameworks
- Applied AI leads at Series A-C startups
- Active GitHub contributors to popular agent / LLM tooling repos
- High-signal community organizers in AI infra space

### sources
- Meta/Novi/Diem alumni networks on LinkedIn filtered by current crypto role (priority: high)
- ETHGlobal alumni and finalist directories from recent hackathons (priority: high)
- Protocol Guild membership list and contributor rosters (priority: high)
- Ethereum Magicians forum and EIP authorship credits (priority: high)
- GitHub search: contributors to major Ethereum/Solana/ZK repos with Meta employment history (priority: high)
- Crypto Twitter/Farcaster accounts known for technical threads with Meta background mentions (priority: medium)
- Devcon and ETHDenver speaker and workshop facilitator lists (priority: medium)
- Warm intros from existing attendees or crypto VC technical networks (priority: medium)
- ZK-focused Telegram and Discord communities (ZK Hack, Aztec Discord, StarkNet Discord) (priority: medium)
- Alumni groups for Meta engineering orgs on LinkedIn (priority: low)

### prioritization_rules
- Warm intros and known builders go to top of queue.
- Founders/engineers actively building in-theme rank higher than investors.
- If two prospects tie on fit, prefer the one with stronger contribution signal (writing, OSS, talks).
- Cap any single company to ~3 attendees to keep room diverse.
- Reject anyone matching avoid personas regardless of company prestige.

## 5. Scoring Rubric
- **Max score:** 100
- **High threshold:** 75
- **Medium threshold:** 55
- **Notes:** Rubric heavily rewards the rare Meta-plus-crypto overlap and verifiable technical depth, with steep penalties for non-builders given the 5-person room has zero slack for mismatched attendees.

## 6. Top 10 Ranked Prospects
| # | Name | Company | Role | Persona | Fit | Priority |
|---|------|---------|------|---------|-----|----------|
| 1 | Avery Ching | Aptos Labs | Co-Founder & CEO | meta_crypto_engineer | 88 | high |
| 2 | Evan Cheng | Mysten Labs | Co-Founder & CEO | meta_crypto_engineer | 88 | high |
| 3 | George Danezis | Mysten Labs / UCL | Co-Founder & Chief Scientist | protocol_hacker | 80 | high |
| 4 | Sam Blackshear | Mysten Labs | Co-Founder & CTO | crypto_open_source_contributor | 78 | high |
| 5 | Kostas Kryptos Chalkias | Mysten Labs | Co-Founder & Chief Cryptographer | zk_specialist | 72 | medium |
| 6 | Adeniyi Abiodun | Mysten Labs | Co-Founder & CPO | community_lead_hacker | 64 | medium |
| 7 | Nassim Eddequiouaq | Bastion | Co-Founder & CEO | defi_smart_contract_dev | 64 | medium |
| 8 | Riyaz Faizullabhoy | Bastion | Co-Founder & CTO | crypto_infra_engineer | 56 | medium |

## 7. Room Balance
- **Summary:** Top 5 prospects: gaps in none; overrepresented: meta_crypto_engineer.
- **Persona breakdown:** {'meta_crypto_engineer': 2, 'protocol_hacker': 1, 'crypto_open_source_contributor': 1, 'zk_specialist': 1}
- **Gaps:**
- **Recommendations:**

## 8. Open Questions
- Is the event public or invite-only?
- Is there a sponsor or partner goal?
- Is the venue already secured?
- What is the exact date and time?
- Who is the primary host / face of the event?

## 9. Next Recommended Ops Actions
- Approve the top high-priority prospects in `data/ranked_people.csv`.
- Hand `data/event_state.json` and `data/ranked_people.csv` to the Agentic Ops branch.
- Run another sourcing pass focused on the top room-balance gap.

