# Agent Activity Log

Human-readable trace of all agent runs in the Eventful branch.

## 2026-05-05T22:48:28.061341+00:00 — objective_agent (`objective_agent-c390b021`)

- **Input:** Raw event brief (733 chars)
- **Output:** Normalized objective for a 100-person hackathon in unspecified city.
- **Reasoning:** Used keyword matching over the brief to infer event size, city, and event type. Goal sentence is the first sentence containing 'goal' or the longest sentence as fallback.
- **Confidence:** medium
- **Decisions:**
  - Inferred event_type='hackathon' from brief keywords.
  - Inferred target_size=100.
  - Inferred city=''.
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-05T22:49:15.885200+00:00 — audience_agent (`audience_agent-7bae8985`)

- **Input:** Objective for 'hackathon' in unspecified city; brief len=733.
- **Output:** Audience designer status=ok; defined 9 ICP personas, 5 avoid personas; target_mix has 9 entries.
- **Reasoning:** Audience design (personas, rubric, target mix) is derived from the event brief by an LLM call — no hardcoded theme libraries. The rubric is rule-based downstream so scores remain auditable. If the LLM is unavailable, a minimal generic fallback keeps the pipeline runnable but won't be theme-specific.
- **Confidence:** high
- **Decisions:**
  - Designer mode: ok.
  - ICP personas: ['smart_contract_developer', 'crypto_native_founder', 'frontend_web3_builder', 'crypto_focused_cs_student', 'defi_protocol_specialist', 'zk_and_infra_engineer', 'ai_crypto_crossover_builder', 'payments_and_wallet_product_builder', 'crypto_curious_technical_operator'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-05T22:57:51.954082+00:00 — sourcing_agent (`sourcing_agent-60ff403b`)

- **Input:** Objective + audience ICP. Seed CSV: False. Curator: ok.
- **Output:** Generated 5 sourcing queries; sourced 170 prospects (curator: ok, target: 100).
- **Reasoning:** Sourcing first calls the LLM curator (web-search-enabled) to find real candidates matching the ICP, sized against target_size from the brief. The rule-based scorer then ranks them. If curator is unavailable (no API key / no SDK), falls back to the optional seed CSV. Either way, downstream scoring is deterministic.
- **Confidence:** medium
- **Decisions:**
  - Built 5 sourcing queries weighted to in-theme builders.
  - Capped per-company attendance at ~3 to preserve room diversity.
  - Curator status: ok.
- **Next actions:**
  - Score prospects with packages/scoring/attendee_fit.py.

## 2026-05-05T22:57:51.960861+00:00 — room_balance_agent (`room_balance_agent-379acd08`)

- **Input:** 170 ranked prospects; target_size=100.
- **Output:** Top 100 prospects: gaps in crypto_focused_cs_student, payments_and_wallet_product_builder; overrepresented: smart_contract_developer, defi_protocol_specialist.
- **Reasoning:** Room balance compares actual persona counts in the top cut to the target mix. A persona is 'gap' if it has <70% of its target slot, and 'overrepresented' at >130%.
- **Confidence:** medium
- **Decisions:**
  - Compared top 100 non-flagged prospects against target mix.
  - Identified 5 persona gap(s).
- **Next actions:**
  - Run sourcing pass focused on top-gap persona.

## 2026-05-05T22:57:51.980372+00:00 — run_intelligence (`run_intelligence-221db472`)

- **Input:** brief=data/event_brief.txt, seed=none
- **Output:** Pipeline complete: 170 prospects scored, 45 high-priority, top_gap=crypto_focused_cs_student.
- **Reasoning:** Sequential pipeline; each stage writes to event_state and emits its own visibility trace.
- **Confidence:** medium
- **Decisions:**
  - Ran objective → audience → sourcing → scoring → room_balance pipeline.
- **Files read:** data/event_brief.txt
- **Files written:** data/event_state.json, data/ranked_people.csv, docs/intelligence_summary.md, docs/structure_map.md
- **Next actions:**
  - Hand event_state.json + ranked_people.csv to Agentic Ops branch.

## 2026-05-06T03:23:25.738285+00:00 — objective_agent (`objective_agent-53ef08b3`)

- **Input:** Raw event brief (56 chars)
- **Output:** Normalized 100-person 'lunch' in unspecified city; goal_len=6, desired_attendees_len=9.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='lunch'.
  - target_size=100, city=''.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T03:23:25.739110+00:00 — audience_agent (`audience_agent-c595a5ff`)

- **Input:** Objective for 'lunch' in unspecified city; effective brief len=170.
- **Output:** Audience designer status=fallback; defined 5 ICP personas, 3 avoid personas; target_mix has 5 entries.
- **Reasoning:** Audience design uses an organizer triad when present (event type, who belongs in the room, overall goal) prepended to the full brief, then one LLM pass — no hardcoded persona libraries. Rubric is rule-based downstream for auditability.
- **Confidence:** low
- **Decisions:**
  - Designer mode: fallback.
  - ICP personas: ['decision_maker', 'hands_on_builder', 'domain_expert', 'community_connector', 'investor_high_signal'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-06T03:23:25.739433+00:00 — sourcing_agent (`sourcing_agent-abd8d4f5`)

- **Input:** Objective + audience ICP. Seed CSV: False. Curator: skipped.
- **Output:** Generated 5 sourcing queries; sourced 0 prospects (curator: skipped, target: 100).
- **Reasoning:** Sourcing first calls the LLM curator (web-search-enabled) to find real candidates matching the ICP, sized against target_size from the brief. The rule-based scorer then ranks them. If curator is unavailable (no API key / no SDK), falls back to the optional seed CSV. Either way, downstream scoring is deterministic.
- **Confidence:** low
- **Decisions:**
  - Built 5 sourcing queries weighted to in-theme builders.
  - Capped per-company attendance at ~3 to preserve room diversity.
  - Curator status: skipped.
- **Next actions:**
  - Score prospects with packages/scoring/attendee_fit.py.

## 2026-05-06T03:23:25.739573+00:00 — room_balance_agent (`room_balance_agent-275086b7`)

- **Input:** 0 ranked prospects; target_size=100.
- **Output:** Top 1 prospects: gaps in hands_on_builder, decision_maker; overrepresented: none.
- **Reasoning:** Room balance compares actual persona counts in the top cut to the target mix. A persona is 'gap' if it has <70% of its target slot, and 'overrepresented' at >130%.
- **Confidence:** medium
- **Decisions:**
  - Compared top 1 non-flagged prospects against target mix.
  - Identified 5 persona gap(s).
- **Next actions:**
  - Run sourcing pass focused on top-gap persona.

## 2026-05-06T03:23:25.740486+00:00 — run_intelligence (`run_intelligence-61ef7e50`)

- **Input:** brief=test, seed=none
- **Output:** Pipeline complete: 0 prospects scored, 0 high-priority, top_gap=hands_on_builder.
- **Reasoning:** Sequential pipeline; each stage writes to event_state and emits its own visibility trace.
- **Confidence:** medium
- **Decisions:**
  - Ran objective → audience → sourcing → scoring → room_balance pipeline.
- **Files read:** test
- **Files written:** /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-0/test_run_pipeline_writes_confi0/state.json, /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-0/test_run_pipeline_writes_confi0/ranked.csv, /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-0/test_run_pipeline_writes_confi0/summary.md, /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-0/test_run_pipeline_writes_confi0/structure_map.md
- **Next actions:**
  - Hand event_state.json + ranked_people.csv to Agentic Ops branch.

## 2026-05-06T03:23:35.367512+00:00 — objective_agent (`objective_agent-dee8f887`)

- **Input:** Raw event brief (56 chars)
- **Output:** Normalized 100-person 'lunch' in unspecified city; goal_len=6, desired_attendees_len=9.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='lunch'.
  - target_size=100, city=''.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T03:23:35.368118+00:00 — audience_agent (`audience_agent-7e9f4f3a`)

- **Input:** Objective for 'lunch' in unspecified city; effective brief len=170.
- **Output:** Audience designer status=fallback; defined 5 ICP personas, 3 avoid personas; target_mix has 5 entries.
- **Reasoning:** Audience design uses an organizer triad when present (event type, who belongs in the room, overall goal) prepended to the full brief, then one LLM pass — no hardcoded persona libraries. Rubric is rule-based downstream for auditability.
- **Confidence:** low
- **Decisions:**
  - Designer mode: fallback.
  - ICP personas: ['decision_maker', 'hands_on_builder', 'domain_expert', 'community_connector', 'investor_high_signal'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-06T03:23:35.368447+00:00 — sourcing_agent (`sourcing_agent-7097fc81`)

- **Input:** Objective + audience ICP. Seed CSV: False. Curator: skipped.
- **Output:** Generated 5 sourcing queries; sourced 0 prospects (curator: skipped, target: 100).
- **Reasoning:** Sourcing first calls the LLM curator (web-search-enabled) to find real candidates matching the ICP, sized against target_size from the brief. The rule-based scorer then ranks them. If curator is unavailable (no API key / no SDK), falls back to the optional seed CSV. Either way, downstream scoring is deterministic.
- **Confidence:** low
- **Decisions:**
  - Built 5 sourcing queries weighted to in-theme builders.
  - Capped per-company attendance at ~3 to preserve room diversity.
  - Curator status: skipped.
- **Next actions:**
  - Score prospects with packages/scoring/attendee_fit.py.

## 2026-05-06T03:23:35.368589+00:00 — room_balance_agent (`room_balance_agent-3e63c487`)

- **Input:** 0 ranked prospects; target_size=100.
- **Output:** Top 1 prospects: gaps in hands_on_builder, decision_maker; overrepresented: none.
- **Reasoning:** Room balance compares actual persona counts in the top cut to the target mix. A persona is 'gap' if it has <70% of its target slot, and 'overrepresented' at >130%.
- **Confidence:** medium
- **Decisions:**
  - Compared top 1 non-flagged prospects against target mix.
  - Identified 5 persona gap(s).
- **Next actions:**
  - Run sourcing pass focused on top-gap persona.

## 2026-05-06T03:23:35.369475+00:00 — run_intelligence (`run_intelligence-fb5daa34`)

- **Input:** brief=test, seed=none
- **Output:** Pipeline complete: 0 prospects scored, 0 high-priority, top_gap=hands_on_builder.
- **Reasoning:** Sequential pipeline; each stage writes to event_state and emits its own visibility trace.
- **Confidence:** medium
- **Decisions:**
  - Ran objective → audience → sourcing → scoring → room_balance pipeline.
- **Files read:** test
- **Files written:** /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-1/test_run_pipeline_writes_confi0/state.json, /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-1/test_run_pipeline_writes_confi0/ranked.csv, /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-1/test_run_pipeline_writes_confi0/summary.md, /private/var/folders/jk/67mvc2_s6qg03h3jgw0828fw0000gn/T/pytest-of-daniel04wang/pytest-1/test_run_pipeline_writes_confi0/structure_map.md
- **Next actions:**
  - Hand event_state.json + ranked_people.csv to Agentic Ops branch.

## 2026-05-06T04:08:35.916092+00:00 — objective_agent (`objective_agent-793db8a2`)

- **Input:** Raw event brief (78 chars)
- **Output:** Normalized 100-person 'small salon' in unspecified city; goal_len=13, desired_attendees_len=18.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='small salon'.
  - target_size=100, city=''.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T04:08:35.917083+00:00 — audience_agent (`audience_agent-5ca2bcf5`)

- **Input:** Objective for 'small salon' in unspecified city; effective brief len=214.
- **Output:** Audience designer status=fallback; defined 5 ICP personas, 3 avoid personas; target_mix has 5 entries.
- **Reasoning:** Audience design uses an organizer triad when present (event type, who belongs in the room, overall goal) prepended to the full brief, then one LLM pass — no hardcoded persona libraries. Rubric is rule-based downstream for auditability.
- **Confidence:** low
- **Decisions:**
  - Designer mode: fallback.
  - ICP personas: ['decision_maker', 'hands_on_builder', 'domain_expert', 'community_connector', 'investor_high_signal'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-06T04:08:35.917659+00:00 — sourcing_agent (`sourcing_agent-c538c55e`)

- **Input:** Objective + audience ICP. Seed CSV: False. Curator: skipped.
- **Output:** Generated 5 sourcing queries; sourced 0 prospects (curator: skipped, target: 100).
- **Reasoning:** Sourcing first calls the LLM curator (web-search-enabled) to find real candidates matching the ICP, sized against target_size from the brief. The rule-based scorer then ranks them. If curator is unavailable (no API key / no SDK), falls back to the optional seed CSV. Either way, downstream scoring is deterministic.
- **Confidence:** low
- **Decisions:**
  - Built 5 sourcing queries weighted to in-theme builders.
  - Capped per-company attendance at ~3 to preserve room diversity.
  - Curator status: skipped.
- **Next actions:**
  - Score prospects with packages/scoring/attendee_fit.py.

## 2026-05-06T04:08:35.918072+00:00 — room_balance_agent (`room_balance_agent-aede730b`)

- **Input:** 0 ranked prospects; target_size=100.
- **Output:** Top 1 prospects: gaps in hands_on_builder, decision_maker; overrepresented: none.
- **Reasoning:** Room balance compares actual persona counts in the top cut to the target mix. A persona is 'gap' if it has <70% of its target slot, and 'overrepresented' at >130%.
- **Confidence:** medium
- **Decisions:**
  - Compared top 1 non-flagged prospects against target mix.
  - Identified 5 persona gap(s).
- **Next actions:**
  - Run sourcing pass focused on top-gap persona.

## 2026-05-06T04:08:35.921587+00:00 — run_intelligence (`run_intelligence-a513c65d`)

- **Input:** brief=POST /run, seed=none
- **Output:** Pipeline complete: 0 prospects scored, 0 high-priority, top_gap=hands_on_builder.
- **Reasoning:** Sequential pipeline; each stage writes to event_state and emits its own visibility trace.
- **Confidence:** medium
- **Decisions:**
  - Ran objective → audience → sourcing → scoring → room_balance pipeline.
- **Files read:** POST /run
- **Files written:** data/event_state.json, data/ranked_people.csv, docs/intelligence_summary.md, docs/structure_map.md
- **Next actions:**
  - Hand event_state.json + ranked_people.csv to Agentic Ops branch.

## 2026-05-06T04:11:05.960757+00:00 — objective_agent (`objective_agent-f2ec237f`)

- **Input:** Raw event brief (71 chars)
- **Output:** Normalized 50-person 'curated dinner' in SF; goal_len=40, desired_attendees_len=0.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='curated dinner'.
  - target_size=50, city='SF'.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T04:11:05.962394+00:00 — audience_agent (`audience_agent-522b89c1`)

- **Input:** Objective for 'curated dinner' in SF; effective brief len=190.
- **Output:** Audience designer status=fallback; defined 5 ICP personas, 3 avoid personas; target_mix has 5 entries.
- **Reasoning:** Audience design uses an organizer triad when present (event type, who belongs in the room, overall goal) prepended to the full brief, then one LLM pass — no hardcoded persona libraries. Rubric is rule-based downstream for auditability.
- **Confidence:** low
- **Decisions:**
  - Designer mode: fallback.
  - ICP personas: ['decision_maker', 'hands_on_builder', 'domain_expert', 'community_connector', 'investor_high_signal'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-06T04:11:05.962861+00:00 — sourcing_agent (`sourcing_agent-8096e531`)

- **Input:** Objective + audience ICP. Seed CSV: False. Curator: skipped.
- **Output:** Generated 5 sourcing queries; sourced 0 prospects (curator: skipped, target: 50).
- **Reasoning:** Sourcing first calls the LLM curator (web-search-enabled) to find real candidates matching the ICP, sized against target_size from the brief. The rule-based scorer then ranks them. If curator is unavailable (no API key / no SDK), falls back to the optional seed CSV. Either way, downstream scoring is deterministic.
- **Confidence:** low
- **Decisions:**
  - Built 5 sourcing queries weighted to in-theme builders.
  - Capped per-company attendance at ~3 to preserve room diversity.
  - Curator status: skipped.
- **Next actions:**
  - Score prospects with packages/scoring/attendee_fit.py.

## 2026-05-06T04:11:05.962981+00:00 — room_balance_agent (`room_balance_agent-decde42f`)

- **Input:** 0 ranked prospects; target_size=50.
- **Output:** Top 1 prospects: gaps in hands_on_builder, decision_maker; overrepresented: none.
- **Reasoning:** Room balance compares actual persona counts in the top cut to the target mix. A persona is 'gap' if it has <70% of its target slot, and 'overrepresented' at >130%.
- **Confidence:** medium
- **Decisions:**
  - Compared top 1 non-flagged prospects against target mix.
  - Identified 5 persona gap(s).
- **Next actions:**
  - Run sourcing pass focused on top-gap persona.

## 2026-05-06T04:11:05.964372+00:00 — run_intelligence (`run_intelligence-42c45078`)

- **Input:** brief=argv, seed=none
- **Output:** Pipeline complete: 0 prospects scored, 0 high-priority, top_gap=hands_on_builder.
- **Reasoning:** Sequential pipeline; each stage writes to event_state and emits its own visibility trace.
- **Confidence:** medium
- **Decisions:**
  - Ran objective → audience → sourcing → scoring → room_balance pipeline.
- **Files read:** argv
- **Files written:** data/event_state.json, data/ranked_people.csv, docs/intelligence_summary.md, docs/structure_map.md
- **Next actions:**
  - Hand event_state.json + ranked_people.csv to Agentic Ops branch.

## 2026-05-06T04:17:29.031713+00:00 — objective_agent (`objective_agent-47527bca`)

- **Input:** Raw event brief (93 chars)
- **Output:** Normalized 100-person 'hackathon' in SF; goal_len=48, desired_attendees_len=0.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='hackathon'.
  - target_size=100, city='SF'.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T04:18:37.526413+00:00 — objective_agent (`objective_agent-eed0671b`)

- **Input:** Raw event brief (93 chars)
- **Output:** Normalized 100-person 'two-day overnight hackathon' in San Francisco; goal_len=74, desired_attendees_len=30.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='two-day overnight hackathon'.
  - target_size=100, city='San Francisco'.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T04:19:28.075525+00:00 — audience_agent (`audience_agent-02c3d2f0`)

- **Input:** Objective for 'two-day overnight hackathon' in San Francisco; effective brief len=318.
- **Output:** Audience designer status=ok; defined 9 ICP personas, 5 avoid personas; target_mix has 9 entries.
- **Reasoning:** Audience design uses an organizer triad when present (event type, who belongs in the room, overall goal) prepended to the full brief, then one LLM pass — no hardcoded persona libraries. Rubric is rule-based downstream for auditability.
- **Confidence:** high
- **Decisions:**
  - Designer mode: ok.
  - ICP personas: ['protocol_engineer', 'zk_cryptographer', 'defi_builder', 'l2_infrastructure_developer', 'crypto_protocol_founder', 'wallet_and_account_abstraction_dev', 'crypto_data_and_indexing_engineer', 'nft_and_onchain_media_builder', 'crypto_devrel_and_tooling_advocate'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-06T04:23:11.659318+00:00 — objective_agent (`objective_agent-c1ee21c4`)

- **Input:** Raw event brief (127 chars)
- **Output:** Normalized 5-person 'hackathon' in unspecified city; goal_len=90, desired_attendees_len=80.
- **Reasoning:** intent_extractor supplies event type, desired attendees, and overall goal when ANTHROPIC_API_KEY is set or when the brief uses labeled sections; size/city still use constraints, intent fields, and regex fallbacks on the full brief.
- **Confidence:** medium
- **Decisions:**
  - event_type='hackathon'.
  - target_size=5, city=''.
  - Captured organizer triad: event type, desired attendees, overall goal (when extractable).
- **Next actions:**
  - Run audience_agent to define ICP and avoid personas.

## 2026-05-06T04:23:47.765430+00:00 — audience_agent (`audience_agent-831bf989`)

- **Input:** Objective for 'hackathon' in unspecified city; effective brief len=400.
- **Output:** Audience designer status=ok; defined 8 ICP personas, 5 avoid personas; target_mix has 8 entries.
- **Reasoning:** Audience design uses an organizer triad when present (event type, who belongs in the room, overall goal) prepended to the full brief, then one LLM pass — no hardcoded persona libraries. Rubric is rule-based downstream for auditability.
- **Confidence:** high
- **Decisions:**
  - Designer mode: ok.
  - ICP personas: ['meta_crypto_engineer', 'protocol_hacker', 'crypto_open_source_contributor', 'zk_specialist', 'community_lead_hacker', 'defi_smart_contract_dev', 'crypto_infra_engineer', 'hackathon_veteran_winner'].
  - High-fit threshold: 75.
- **Next actions:**
  - Run sourcing_agent to define queries and (optionally) curate via web search.

## 2026-05-06T04:24:40.607308+00:00 — sourcing_agent (`sourcing_agent-bb6d6f26`)

- **Input:** Objective + audience ICP. Seed CSV: False. Curator: ok.
- **Output:** Generated 5 sourcing queries; sourced 8 prospects (curator: ok, target: 5).
- **Reasoning:** Sourcing first calls the LLM curator (web-search-enabled) to find real candidates matching the ICP, sized against target_size from the brief. The rule-based scorer then ranks them. If curator is unavailable (no API key / no SDK), falls back to the optional seed CSV. Either way, downstream scoring is deterministic.
- **Confidence:** medium
- **Decisions:**
  - Built 5 sourcing queries weighted to in-theme builders.
  - Capped per-company attendance at ~3 to preserve room diversity.
  - Curator status: ok.
- **Next actions:**
  - Score prospects with packages/scoring/attendee_fit.py.

## 2026-05-06T04:24:40.608915+00:00 — room_balance_agent (`room_balance_agent-0f124470`)

- **Input:** 8 ranked prospects; target_size=5.
- **Output:** Top 5 prospects: gaps in none; overrepresented: meta_crypto_engineer.
- **Reasoning:** Room balance compares actual persona counts in the top cut to the target mix. A persona is 'gap' if it has <70% of its target slot, and 'overrepresented' at >130%.
- **Confidence:** medium
- **Decisions:**
  - Compared top 5 non-flagged prospects against target mix.
  - Identified 0 persona gap(s).
- **Next actions:**
  - Proceed to outreach prioritization.

## 2026-05-06T04:24:40.611641+00:00 — run_intelligence (`run_intelligence-630f2f46`)

- **Input:** brief=POST /run, seed=none
- **Output:** Pipeline complete: 8 prospects scored, 4 high-priority, top_gap=none.
- **Reasoning:** Sequential pipeline; each stage writes to event_state and emits its own visibility trace.
- **Confidence:** medium
- **Decisions:**
  - Ran objective → audience → sourcing → scoring → room_balance pipeline.
- **Files read:** POST /run
- **Files written:** data/event_state.json, data/ranked_people.csv, docs/intelligence_summary.md, docs/structure_map.md
- **Next actions:**
  - Hand event_state.json + ranked_people.csv to Agentic Ops branch.

