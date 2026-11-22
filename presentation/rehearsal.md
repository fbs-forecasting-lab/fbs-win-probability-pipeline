# Five-minute final demo rehearsal

Estimated 4:40 including transitions. Assign each blank speaker slot before timing the talk aloud. Stop speaking by 5:00. Reserve the extra minute for questions.

Rubric: stakeholders (3 points), slide 1; market research (3), slide 2; methodology including clarity and reproducibility (10), slides 3–4; limitations (2) and conclusion (2), slide 5.

## Slide 1

0:00–0:39 ESTIMATE  |  Speaker: __________

Imagine writing a college football preview. Saying the home team will win hides the most useful part of the story: how surprising would an away win be? A fan wants a favorite. A reporter also needs a sense of uncertainty. A data engineer needs to know which games and model produced the estimate before anyone quotes it. Our submitted stakeholder analysis identified all three needs. We built the demo around one probability and the evidence behind it. Here is where that fits in the research.

Q&A (after the talk)
Who else was identified? Bettors, fantasy players and coaching staff. The model has no player-level injury or lineup inputs.

## Slide 2

0:39–1:18 ESTIMATE  |  Speaker: __________

Two studies from our market research helped us define the question. South and Egros looked at score differences across several seasons. Coleman combined rating systems and evaluated their margin predictions against betting lines. Those approaches ask what a method can predict. We added a systems question: can another person trace and reproduce a probability after the input changes? We saved the inputs, linked each result to its model, and monitored the batch. Our own small sportsbook comparison comes later. It is separate from this review of prior work.

Q&A (after the talk)
Did we outperform either paper? These studies use different targets and data. We compared our probabilities against a constant baseline on our own holdout.

## Slide 3

1:18–2:57 ESTIMATE  |  Speaker: __________

Follow the left side first. An ingestion Lambda calls College Football Data and stores the response and its receipt in private S3. A preparation Lambda normalizes the selected games. Athena builds the features from the selected sources. Python checks the SQL results before the dataset is published. For each matchup, subtract the visiting team’s prior-season win rate from the home team’s. Do the same for average scoring margin. Add one for a home field or zero for a neutral site. The label is whether the home team won. SageMaker learned the scaling and logistic regression coefficients from 2,194 games in 2022 through 2024. We held out all 740 games from 2025 for evaluation. An independent Lambda verified the managed model’s receipt, reloaded it and scored a saved 2026 sample. Now follow the right side. Step Functions coordinated a separate weekly demonstration. That worker reused the protected model from our earlier Lambda training run. We did not switch that deployment to the SageMaker model. The weekly capture must be observed before a fixed cutoff and kickoff must still be ahead. That prevents a late snapshot from qualifying. It cannot tell us when a historical statistic was originally public. That is why the saved examples carry retrospective status. Let’s see what a probability from the verified managed model looks like.

Q&A (after the talk)
Why two producers? Each verified run has its own provenance. Which step ran locally? The historical graded processing ran in AWS. The separate fictional quickstart is for onboarding.

## Slide 4

2:57–3:49 ESTIMATE  |  Speaker: __________

These two numbers came from a genuine inference call with a hypothetical matchup. The home team won twenty percentage points more games last season, had an average margin seven points higher, and plays at home. The model assigned 66.24 percent to home and 33.76 percent to away. On a different call the same bridge reproduced every byte of the saved predictions for 59 games. That checks reproducibility. For performance we need outcomes, so we turn to the 740 games from 2025. Brier score averages squared probability errors. Lower is better. Our model scored 0.211 against 0.242 for a baseline that always predicts the historical training home-win rate. How do we judge a newer batch before its outcomes arrive?

Q&A (after the talk)
Other holdout metrics: model vs constant log loss 0.6096 vs 0.6763; accuracy 66.49% vs 59.19%. Exact service fit count lacks independent CloudWatch corroboration.

## Slide 5

3:49–4:40 ESTIMATE  |  Speaker: __________

Here is a saved reading from the Week 13 monitoring report. Ten of 65 games had kickoff times listed as to be determined. That pushed quarantine above its ten percent warning threshold. We cannot check whether a game starts after the cutoff without a time, so keep those games out and inspect schedule coverage. The batch contained 53 scored games, all awaiting outcomes. The 740 historical holdout games cannot supply those missing labels. Only five of the 53 matched a bookmaker under our timestamp and matchup rules. That gives comparison coverage, not evidence of betting skill. We demonstrated traceable probabilities, reproducible scoring and a warning that changes how you read a result. Operational approval still needs verified publication times, observed outcomes and genuine review. Thank you.

Q&A (after the talk)
Does the warning establish drift? No. It measures missing kickoff times. Has a human investigation been documented? No genuine finding is claimed. Why no rolling Brier? Every Week 13 label was pending in the saved report.

Test the downloaded PPTX in Slide Show on the classroom computer, check widescreen scaling and Presenter View, disconnect the network for one run, and time all handoffs. Submit the actual PPTX by December 1 at 9 a.m. Eastern. Attendance is required.
