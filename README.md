# llama-jev

_This is currently a work in progress_

# Goal

I created this repository as an experiment to implement a [jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) like API on top of `llama.cpp` server. Here are my goals from this experiment:

- Understand how `jev` works by trying to mimic it myself
- Understand the limitations of current LLMs and why did [TypeSafe AI](https://typesafe.ai) need to create a new type of model
- Have fun solving a new challenge
- Publish a working solution (if any) as an open source library or cli tool, or contribute it to llama.cpp (and other open source inference engines)

# Current results

I use the 231 downloadable [JevBench](https://benchmarkheaven.com/jev-models) tasks to evaluate this implementation locally. Public accuracy is the direct comparison available against [JevBench v1.4.2's published results](https://github.com/fstandhartinger/jevbench/blob/main/results/v1.4.2/jevbench-v1.4.2-results.json):

| System                          | Correct public tasks | Public accuracy |
| ------------------------------- | -------------------: | --------------: |
| Jev 1.13.0                      |              200/231 |           86.6% |
| minicpm5-2b-q8 (llama-jev)      |              150/231 |           64.9% |
| granite4.2-3b-q6 (llama-jev)    |              150/231 |           64.9% |
| lfm2-2.6b-q8 (llama-jev)        |              151/231 |           65.4% |
| ministral3-3b-q8 (llama-jev)    |              160/231 |           69.3% |

_Bigger models scored better: 191/231 (82.7%) for `qwen3.6-35b-a3b-q6` and 198/231 (85.7%) for `qwen3.8-27b-q6`, but I decided to only include models that fit in 16GB to have comparable speed and cost to jev_

The scores below use only the public dataset. Their score proxies are local benchmark estimates, not Jev leaderboard scores. The $0.10/hour estimate assumes a comparable-performance rental GPU with 16GB VRAM.

## Jev leaderboard scores

| System     | Intelligence | Calibration | Capability | Speed | Cost |    $/1k | JevBench Score |
| ---------- | -----------: | ----------: | ---------: | ----: | ---: | ------: | -------------: |
| Jev 1.13.0 |         53.1 |        76.3 |       64.7 |  83.3 | 52.0 | $0.0399 |           63.3 |

## llama-jev public-dataset scores

| Model            | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| ---------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| minicpm5-2b-q8   |         48.9 |        31.9 |       40.4 |  82.1 | 76.3 |   $0.0062 |        49.8 |
| granite4.2-3b-q6 |         50.7 |        20.6 |       35.6 |  78.8 | 70.0 |   $0.0100 |        42.0 |
| lfm2-2.6b-q8     |         50.4 |        16.4 |       33.4 |  80.4 | 72.9 |   $0.0080 |        37.4 |
| ministral3-3b-q8 |         57.4 |        62.5 |       60.0 |  79.5 | 70.3 |   $0.0098 |        66.4 |

# Next steps

- Improve the implementation and test it on other models
- Publish it as a library or cli tool

# Developement process and documentation

I am building this in public, so I will be documenting each step of the process in [docs/story.md](docs/story.md) and commiting the code changes as I go
