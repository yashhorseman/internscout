-- which prompt file produced each chat call, so changes can be compared
alter table llm_calls add column prompt_version text;
