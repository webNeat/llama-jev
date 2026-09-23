# llama-jev

_This is currently a work in progress_

# Goal

I created this repository as an experiment to implement a [jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) like API on top of `llama.cpp` server. Here are my goals from this experiment:

- Understand how `jev` works by trying to mimic it myself
- Understand the limitations of current LLMs and why did [TypeSafe AI](https://typesafe.ai) need to create a new type of model
- Have fun solving a new challenge
- Publish a working solution (if any) as an open source library or cli tool, or contribute it to llama.cpp (and other open source inference engines)

# Current results

I am using the [JevBench](https://benchmarkheaven.com/jev-models) **public tests** to evaluate the implementation locally on a Strix Halo GPU.

_score = (intelligence + calibration + speed) / 3_

**jev** (scores from the benchmark leaderboard for reference, they include hidden tasks)

| Dataset  | Intelligence | Calibration | Speed | Score |
| -------- | ------------ | ----------- | ----- | ----- |
| easy     | 100          | 83          | 83    | 88.3  |
| easy + standard | 99         | 83        | 83  | 88   |
| hard     | 61         | 83        | 83  | 74.6   |
| global   | 86         | 83        | 83  | 83.9  |


**minicpm5-2b Q8:**

| Dataset  | Intelligence | Calibration | Speed | Score |
| -------- | ------------ | ----------- | ----- | ----- |
| easy     | 85.4         | 80.9        | 92.2  | 86.2  |
| easy + standard | 45.2  | 70.5        | 92.2  | 69.3  |
| hard     | 13.1         | 34.8        | 81.9  | 43.3  |
| global   | 28.8         | 54.3        | 85.0  | 56.0  |

_Note: the speed is adjusted for local run `latency = local_latency_seconds * 2.0 + 0.15`_

_I will add results for other models soon_

# Next steps

- Improve the implementation and test it on other models
- Publish it as a library or cli tool

# Developement process and documentation

I am building this in public, so I will be documenting each step of the process in [docs/story.md](docs/story.md) and commiting the code changes as I go
