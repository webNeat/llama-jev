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
| minicpm5-2b Q8 (llama-jev)     |              149/231 |           64.5% |
| qwen3.6-35b-a3b Q6 (llama-jev) |              191/231 |           82.7% |
| qwen3.8-27b Q6 (llama-jev)     |              198/231 |           85.7% |

## Jev leaderboard scores

| System     | Intelligence | Calibration | Capability | Speed | Cost |    $/1k | JevBench Score |
| ---------- | -----------: | ----------: | ---------: | ----: | ---: | ------: | -------------: |
| Jev 1.13.0 |         53.1 |        76.3 |       64.7 |  83.3 | 52.0 | $0.0399 |           63.3 |

## llama-jev public-dataset scores

**minicpm5-2b-q8**

| Public dataset | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| -------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| Easy           |         97.1 |        96.6 |       96.9 |  90.7 | 77.1 |   $0.0058 |        89.6 |
| Standard       |         51.6 |        48.3 |       50.0 |  90.6 | 76.6 |   $0.0060 |        62.3 |
| Hard           |         22.6 |        23.5 |       23.0 |  79.2 | 53.0 |   $0.0370 |         6.9 |
| All public     |         48.4 |        23.5 |       35.9 |  82.0 | 60.4 |   $0.0208 |        40.7 |

**qwen3.6-35b-a3b-q6**

| Public dataset | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| -------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| Easy           |        100.0 |        99.9 |      100.0 |  79.3 | 51.3 |   $0.0420 |        76.8 |
| Standard       |         91.9 |        94.0 |       93.0 |  79.3 | 51.1 |   $0.0427 |        74.5 |
| Hard           |         51.1 |        67.4 |       59.3 |  67.3 | 33.8 |   $0.1613 |        23.1 |
| All public     |         76.5 |        67.4 |       72.0 |  71.0 | 40.1 |   $0.0995 |        38.3 |

**qwen3.8-27b-q6**

| Public dataset | Intelligence | Calibration | Capability | Speed | Cost | $/1k est. | Score proxy |
| -------------- | -----------: | ----------: | ---------: | ----: | ---: | --------: | ----------: |
| Easy           |        100.0 |        99.9 |      100.0 |  71.9 | 39.6 |   $0.1034 |        42.3 |
| Standard       |         96.0 |        93.3 |       94.6 |  70.9 | 38.7 |   $0.1106 |        39.2 |
| Hard           |         57.9 |        79.0 |       68.4 |  59.0 | 20.5 |   $0.4453 |         7.1 |
| All public     |         80.9 |        79.0 |       79.9 |  62.6 | 27.1 |   $0.2699 |        15.0 |

_Note: The local cost estimate uses a [Strix Halo rental reference](https://gpurack.net/pricing) and the active request time_

# Next steps

- Improve the implementation and test it on other models
- Publish it as a library or cli tool

# Developement process and documentation

I am building this in public, so I will be documenting each step of the process in [docs/story.md](docs/story.md) and commiting the code changes as I go
