# llama-jev

_This is currently a work in progress_

# Goal

I created this repository as an experiment to implement a [jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) like API on top of `llama.cpp` server. Here are my goals from this experiment:

- Understand how `jev` works by trying to mimic it myself
- Understand the limitations of current LLMs and why did [TypeSafe AI](https://typesafe.ai) need to create a new type of model
- Have fun solving a new challenge
- Publish a working solution (if any) as an open source library or cli tool, or contribute it to llama.cpp (and other open source inference engines)

# Current results

I use the 231 downloadable [JevBench](https://benchmarkheaven.com/jev-models) tasks to evaluate this implementation locally on a Strix Halo GPU.

Public accuracy is the only direct comparison available against [JevBench v1.4.2's published results](https://github.com/fstandhartinger/jevbench/blob/main/results/v1.4.2/jevbench-v1.4.2-results.json):

| System                         | Correct public tasks | Public accuracy |
| ------------------------------ | -------------------: | --------------: |
| Jev 1.13.0                     |              200/231 |           86.6% |
| minicpm5-2b Q8 (llama-jev)     |              121/231 |           52.4% |
| qwen3.6-35b-a3b Q6 (llama-jev) |              160/231 |           69.3% |
| qwen3.8-27b Q6 (llama-jev)     |              122/231 |           52.8% |

## Jev leaderboard scores

| System     | Intelligence | Calibration | Capability | Speed | Cost |    $/1k | JevBench Score |
| ---------- | -----------: | ----------: | ---------: | ----: | ---: | ------: | -------------: |
| Jev 1.13.0 |         53.1 |        76.3 |       64.7 |  83.3 | 52.0 | $0.0399 |           63.3 |

## llama-jev public-dataset scores

**minicpm5-2b-q8**

| Public dataset | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| -------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| Easy           |         85.4 |        81.0 |       83.2 |  91.4 | 78.1 |   $0.0054 |        83.7 |
| Standard       |         17.3 |        46.0 |       31.7 |  90.9 | 77.5 |   $0.0056 |         4.7 |
| Hard           |         13.1 |        35.5 |       24.3 |  79.6 | 53.6 |   $0.0351 |         2.0 |
| All public     |         28.8 |        35.5 |       32.2 |  82.4 | 61.1 |   $0.0197 |        14.6 |

**qwen3.6-35b-a3b-q6**

| Public dataset | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| -------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| Easy           |         97.1 |        89.0 |       93.0 |  81.9 | 56.3 |   $0.0286 |        77.7 |
| Standard       |         67.7 |        73.5 |       70.6 |  82.0 | 55.9 |   $0.0296 |        68.4 |
| Hard           |         26.7 |        42.8 |       34.7 |  68.1 | 35.1 |   $0.1452 |         5.4 |
| All public     |         56.4 |        42.8 |       49.6 |  72.3 | 42.1 |   $0.0849 |        36.1 |

**qwen3.8-27b-q6**

| Public dataset | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| -------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| Easy           |         65.1 |        70.0 |       67.5 |  77.0 | 49.3 |   $0.0491 |        61.7 |
| Standard       |         53.6 |        48.0 |       50.8 |  76.6 | 48.4 |   $0.0524 |        51.2 |
| Hard           |          0.0 |        14.3 |        7.1 |  59.7 | 21.7 |   $0.4089 |         0.0 |
| All public     |         33.5 |        14.3 |       23.9 |  64.5 | 29.5 |   $0.2230 |         4.2 |

_Note: The local cost estimate uses a [Strix Halo rental reference](https://gpurack.net/pricing) and the active request time_

# Next steps

- Improve the implementation and test it on other models
- Publish it as a library or cli tool

# Developement process and documentation

I am building this in public, so I will be documenting each step of the process in [docs/story.md](docs/story.md) and commiting the code changes as I go
