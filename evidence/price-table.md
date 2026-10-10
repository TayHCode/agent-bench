# Historical price assumptions

Recorded list prices in USD per million tokens, version 2026-10-09. These assumptions reproduce the published cost equivalents; they are not current quotes.

Sources: https://www.anthropic.com/pricing and https://openai.com/api/pricing/ . The original experiments recorded these on 2026-10-09, with Sonnet cache reads corrected on 2026-10-10.

| Model | Input | Output | Cache read | Cache write (1h) | Cache write (5m) |
|---|---|---|---|---|---|
| claude-haiku-5-5 | 0.1 | 0.5 | 0.01 | 0.2 | 0.125 |
| claude-sonnet-5-5 | 2.0 | 10.0 | 0.2 | 4.0 | 2.5 |
| claude-opus-5-5 | 4.0 | 20.0 | 0.2 | 8.0 | 5.0 |
| gpt-6-astra | 10.0 | 50.0 | 1.0 | 10.0 | 10.0 |
| gpt-6.1-sol | 2.0 | 10.0 | 0.1 | 2.0 | 2.0 |

Haiku contexts above 100,000 tokens use the recorded 5x multiplier. OpenAI cache writes are counted at the input rate. Subscription usage is reported as dollar-equivalent, not a bill.
