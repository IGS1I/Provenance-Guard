## Project Description
Provenenace Guard is a backend system that any creative sharing platform could plug into to classify submitted content as either human or AI, score confidence in that classification, surface a transparency label to users, and handle appeals from creators who believe they've been misclassified.

There is an API content submission endpoint that accepts a piece of text-based content (a poem, a short story excerpt, a blog post) for attribution analysis.

The endpoint returns a structures response including the attributtion result, confidence score, and the transparency label text that would be shown to the user for them to know whether to believe that the content is human or AI.

## Tool Stack

| Component | Tool | Notes |
| --------- | ---- | ----- |
API framework | Flask | Free, lightweight |
Detection signal 1 | Groq (llama-3.3-70b-versatile) | Free tier — same account as Projects 1–3 |
Detection signal 2 | Stylometric heuristics | Pure Python, no external libraries needed |
Rate limiting | Flask-Limiter | Free
Audit log | SQLite (built-in) or structured JSON | No additional setup |

## Detection Pipeline: Multi-signal
<!--
Name and explain 2 or more detection signals: what they capture, what tool they use, and what they miss.
-->

These detection signals are what emotions and types of words the model should focus on when combing through the submitted content.

| Signals | What's captured? | Tool Used | What's missed? |
| ------- | ---------------- | --------- | -------------- |
|Style and Semantics| Semantic and stylistic structural writing differences between humans and AI| Groq (llama-3) | Emotional writing not particularly looked for |
|Heuristics| Statistical properties differing between human and AI writing; sentence length variance, type-token ratio (vocab diversity), punctuation density, or average sentence complexity | Stylometric heuristics via Python | Word meanings are overlooked |
|  |  |  |  |

## Confidence Scoring

<!--
Explain the confidence score and how it is derived from detection signals, as well as how uncertainty will be addressed.
-->

Based on the above detection signals, a confidence score is derived and therefore expressed via plain decimal numbering and a transparency label, as well as an explanation as to why the label was chosen.

The detection signals should be comparing the content to AI's method of writing, to which a score is averaged out across, which is the confidence score.

The explanation is meant to demistify uncertainty of Provenance Guard's classification.

If Provenance Guard misclassifies a human writer's work as AI (a false positive), the system would have received an appeal. Based on that it will inspect the results from its tools, rescore the content, and present it to the user. If the work is still misclassified, the user should explain more in the appeal as to what makes it human content and the system will check against a more computationally expensive heuristics tool and a known AI-generation bit of content, mark it as such, return the result from its new information and tools, and keep that knwoledge going forward.

## Transparency Labels

<!--
Explain the transparency labels going to be used, how the model why they fit well, and which use cases they fit with. Explain variants if existing.
-->

**Confidently AI** - content the system believes it should have gotten correct (confidence score < 0.45)

**Uncertain** - content the system is terribly unconfident about. ( 0.45 <= confidence score <= 0.54)

**Confidently Human** - content the system believes is exactly what it was labeled/classified as (confidence score > 0.54)

These labels are chosen to properly convey to the user/creator how likely the content they submitted is either human or AI. The confidence score plays the biggets role in deciding the label and scrutiny is taken on how confident Provenence Guard should be when classifying teh content.

## Architecture
```Mermaid
---
title: Provenance Guard Architecture
---
graph TD
    A(Content Submission) --> B(Tool Dissection) --> C(Confidence Scoring) --> J(Decide Transparency Label) -->|Results logged on audit| D(Showcase of classification (confidence score, transparency label) to creator)
    D --> F(Creator appeals) --> G(Creator inputs an appeal reason) -->|Appeal is logged | H(Appeal reason shown beside original classification)

    %% Re-classification
    H -->| Content status set to under review |I(Submission is re-classified based on appeal reasoning)
    I --> D
    D --> J(Creator accepts classifcation)
```

## Appeals Workflow

If creators wish to contest the classification, here is an appeal flow available to follow:

```Mermaid
---
title: Appeal Mechanism
---
graph LR
    A([Creator inputs an appeal reason]) -->|Appeal is logged | B(Appeal reason shown beside original classification)

    %% Re-classification
    B -->| Content status set to under review |C[Submission is re-classified based on appeal reasoning]
```

## Rate Limiting

Provenance Guard will only be allowed to be used infinitely by creators with a one minute delay inbetween. Appeals can only occur three times per classification.

Summary:
- **1-minute delay per classification**
- **5 appeals per classification**

## Auditing: Appeals workflow

<!--
Explain how users can appeal the results. Explain at least two anticipated edge cases.
-->
Attributions (confidence score, signals used, and appeals) decisions are documented on an audit log.

3 audit log entry examples:

## Edge Cases

1) Perhaps a creator inputs complete AI content and the system tries to prove the content submitted is human, therefore missing and misclassifying the content as AI.

2) The content could have text in it that is recognized as image data or some other code or format, which perhaps the system is weak at recognizing as human or AI, given that the system is meant for forums and paragrpahs about different subjects.

## AI Tool Plan

<!--
Example of how AI will be used for this project.
-->
*M3: Submission Endpoint + First Signal*
Input: planning.md + requirements.txt + "Here is my planning.md, a plan for Provenance Guard. May you please build out my system and offer improvements to my plan for me to ask you about later? Especially the labeleling and scoring method."

Desired output: Improvement to current plan. Milestone 3 completed and objective implemented.

POST /submit returns a JSON response including content_id, attribution result, and a placeholder confidence score. Each submission writes a structured entry to the audit log. GET /log returns those entries as JSON.

*M4: Second Signal + Confidence Scoring*
Input: planning.md + "Here is my planning.md, a plan for Provenance Guard. May you please build out my system and offer improvements to my plan for me to ask you about later?"

Desired output: Milestone 4 completed and objective implemented.

Both detection signals are running and their outputs are combined into a single confidence score. Submitting clearly AI-generated text produces a noticeably different score than clearly human-written text. The audit log records individual signal scores and the combined result.

*M5: Production Layer*
Input: planning.md + "Here is my planning.md, a plan for Provenance Guard. May you please build out my system and offer improvements to my plan for me to ask you about later?"

Desired output: Milestone 5 completed and objective implemented.

All four production features are working: the transparency label varies by confidence level, appeals can be submitted and are reflected in the audit log, rate limiting triggers when the limit is exceeded, and the audit log has at least 3 structured entries covering submissions and at least one appeal. All of these work end-to-end without workarounds.

# Stretch Features

## Ensemble Detection
<!--
Incorporate 3 or more detection signals with a documented wighting or voting approach
-->

## Provenence Certficate
<!--
Design and implement a "verified human" credential that a creator can earn through an additional verfication step, including how it's displayed on their content.
-->

## Analytics Dashboard
<!--
Build a simple view showing detection pattersn , appaeal rates, and one additional metric.
-->

## Multi-Modal Support
<!--
Extend the pipeline to handle a second content (e.g., image desctiptions or structured metadata) in addition to text.
-->