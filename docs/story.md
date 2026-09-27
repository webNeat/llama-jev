# Context

- **Hardware:** AMD Strix Halo (Ryzen AI Max+ 395) with 48GB VRAM and 48GB RAM
- **OS:** Ubuntu 25.10
- **Inference:** `llama.cpp`
- **Programming language:** Typescript, I may switch to another language if needed later
- **LLM:** `minicpm5-2b-q8` with `LLAMA_CTX=262144` and `LLAMA_PARALLEL=8` which gives 8 parallel instances with 32k context each

# Step 1: Definitions and mental model

Let me start by sharing my understanding of what an LLN is from a developer perspective and what `jev` API is.

**What is an LLM?**

For the purposes of this experiment, an LLM is a black box that takes a list of tokens and returns probabilities of the next token, it can be modeled by the following function:
```ts
function llm(tokens: string[]): Record<string, number> {...}
```

Based on this function we can implement the `generate` function taking a prompt and returning a full response:
```ts
function generate(prompt: string): string {
  let response = ''
  while (true) {
    const choices = llm(get_tokens(prompt))
    const token = choose_token(choices)
    if (token === SPECIAL_END_TOKEN) break
    response += token
    prompt += token
  }
  return response
}
```
Where:
- `get_tokens` takes a text and split it into list of tokens (words or part of words)
- `choose_token` picks a token randomly based on the probability distribution
- `SPECIAL_END_TOKEN` a special token meaning the end of the response

**What is `jev`? how is it different from a normal LLM?**

For me `jev` is a black box that takes some `state` and a list of classification `questions` about that data, and returns answers of the given questions.
- The `state` can be a bunch of text, images, etc.
- A classification question can be:
  - A true/false question, in which case the answer is the probability of the answer being `true`
  - A multiple choices question, in which case the answer is the probabilities of choices being correct
  - A scoring question, which I don't fully understand.
- The answer of each question also includes a percentage showing how confident is the model

On the rest of this experiment, I will be focusing on the multiple choices question type, because I think the other two types can be derived from it or implemented in similar way.

So, for the purpose of this experiment, `jev` API can be represented by the following function:
```ts
function jev(state: unknown, questions: Record<string, Question>): Record<string, Answer> {...}

type Question = {
  instructions: string // What the model should decide
  criteria: Record<string, string> // A map of option/choice to its description
}
type Answer = {
  choice: string // The highest-probability option
  probabilities: Record<string, number>
  confidence: number
}
```

# Step 2: Getting the next token probabilities using `llama.cpp`

**Setup:** llama.cpp running on port 8080 with model `minicpm5-2b-q8`.

Let's start by using the `/completion` endpoint of `llama.cpp` to get the probabilities of the next token:

```ts
fetch('http://localhost:8080/completion', {
  method: 'POST',
  body: JSON.stringify({
    prompt: `Question: Who discovered the theory of relativity. Answer: `,
    n_predict: 1, // number of tokens to predict
    n_probs: 5, // number of next token probabilities to return
  }),
})
```

A subset of the response is:
```json
{
  "prompt": "Question: Who discovered the theory of relativity. Answer:",
  "content": " Albert",
  "completion_probabilities": [
    {
      "token": " Albert",
      "logprob": -0.013853824697434902,
      "top_logprobs": [
        { "token": " Albert", "logprob": -0.013853824697434902 },
        { "token": " Einstein", "logprob": -4.825379371643066 },
        { "token": " Galileo", "logprob": -6.903128623962402 },
        { "token": " Isaac", "logprob": -7.485108375549316 },
        { "token": " General", "logprob": -7.8169050216674805 }
      ]
    }
  ]
}
```

**Notes:**
- We need to provide `n_probas` to tell `llama.cpp` how many token choices we want in the response, in the example above only the 5 most probable tokens are returned
- The probabilities are given in log, we need to apply `exp` to get the probabilty value between 0 and 1

So we can implement the following function
```ts
async function next_token_probs(prompt: string, n_probs: number) {...}

const probs = await next_token_probs(`Question: Who discovered the theory of relativity. Answer:`, 5)
console.log(JSON.stringify(probs, null, 2))
```

```json
{
  " Albert": 0.9862416979053477,
  " Einstein": 0.008023509400994375,
  " Galileo": 0.0010046373745134945,
  " Isaac": 0.0005613823265568952,
  " General": 0.0004028666187406216
}
```

So 98.6% for "Albert", 0.8% for "Einstein" and the rest for other choices.

Let's measure how much time it takes to return these probabilities:
```ts
for (let i = 0; i < 5; i++) {
  const start = performance.now()
  await next_token_probs(`Question: Who discovered the theory of relativity. Answer:`, 5)
  const duration = performance.now() - start
  console.log(Math.floor(duration) + 'ms')
}
```

After restarting the server (to clear the KV cache) and running the snippet above:
```
46ms
16ms
15ms
16ms
16ms
```

So the first request with no cache takes 46ms, and subsequent requests take 16ms.

# Step 3: First `jev` implementation

Let's implement the first version of the `jev` classifier, it will take a single multi-choice question and return the choices probabilities.

```ts
type Question = {
  instructions: string
  choices: Record<string, string>
}
async function jev(state: string, question: Question) {...}
```

The first idea I have is to use the `next_token_probs` function we implemented earlier with the following prompt:

```
${state}
---
Question: ${question.instructions}
Answer:
```

And check the probabilities of the given choices inside the returned probabilities. But here are the issues with this approach:
1. Let's say I set `n_probs = 100`, then there is no garantee that the given `question.choices` will be part of the returned top 100 tokens
2. Some given `question.choices` may not fit on a single token

As an attempt to work around these issues, let's rewrite the prompt to:
```
${state}

---

Question: ${question.instructions}

Choices:
  1. ${choices 1}: ${description of choice 1}
  2. ${choices 2}: ${description of choice 2}
  3. ${choices 3}: ${description of choice 3}

Number of the correct choice:
```

This should force the model to suggest `1`, `2` or `3` as the next token.

I implemented the `jev` function with this last prompt and made it return the probabilities of the top 10 tokens, here is an example:

_Code call_
```ts
await jev(
  "Our API integration started returning 500 errors on every request about 20 minutes ago, and we can't process any customer orders until this is fixed.",
  {
    instructions: 'Which team should handle this',
    choices: {
      billing: 'Payment or subscription issues',
      technical: 'Bugs or integration problems',
      sales: 'Pricing or account questions',
    },
  }
)
```

_prompt_
```
Our API integration started returning 500 errors on every request about 20 minutes ago, and we can't process any customer orders until this is fixed.

---

Question: Which team should handle this

Choices:
  1. billing: Payment or subscription issues
  2. technical: Bugs or integration problems
  3. sales: Pricing or account questions

Number of the correct choice: 
```

_probabilities of next token_
```json
{
  "0": 0.00025871295978876374,
  "1": 0.2758248382478804,
  "2": 0.685222093120562,
  "3": 0.03817516278429753,
  "4": 0.00042943882754722425,
  "5": 0.000033590968600205436,
  "6": 0.00001288515479935798,
  "7": 0.00000785177267960736,
  "9": 0.0000040027582244881494,
  " ?\n": 0.000003914160768610566
}
```

Which means:
- billing: 27.5%
- technical: 68.5%
- sales: 3.8%

Oh, this seems to work correctly, at least for this example, even with my small **2b Q8 model** :) and it took **80ms without cache and 40ms with cache**

Now let's make the `jev` function return the choices probabilities, now we can write code like the following:
```ts
const state = "Our API integration started returning 500 errors on every request about 20 minutes ago, and we can't process any customer orders until this is fixed."

const department = await jev(state, {
  instructions: 'Which team should handle this',
  choices: {
    billing: 'Payment or subscription issues',
    technical: 'Bugs or integration problems',
    sales: 'Pricing or account questions',
  },
})

const is_urgent = await jev(state, {
  instructions: 'The message conveys urgency or time-sensitivity',
  choices: { yes: '', no: '' },
})

console.log({department, is_urgent})
```

```json
{
  "department": {
    "billing": 0.2777646287584465,
    "technical": 0.6819939599746903,
    "sales": 0.039515127307207853
  },
  "is_urgent": {
    "yes": 0.9290248162812628,
    "no": 0.07008685505786921
  }
}
```

# Step 4: Handling multiple questions in parallel

The easiest way to handle multiple questions is to call the `next_token_probs` function concurrently for each question then collect the answers.
With that change, the code is:
```ts
const res = await jev(state, {
  department: {
    instructions: 'Which team should handle this',
    choices: {
      billing: 'Payment or subscription issues',
      technical: 'Bugs or integration problems',
      sales: 'Pricing or account questions',
    },
  },
  is_urgent: {
    instructions: 'The message conveys urgency or time-sensitivity',
    choices: { yes: '', no: '' },
  },
})
```

It prints the same results as above and takes **80ms**

# Step 5: Adding confidence

Now we need to add a confidence score to the answers, one way to do it is by adding a "I am not sure" and compute the confidence as `1 - unsure_probability`. Another way is to give the probabilities to the model and ask about its confidence directly.
I went with the first way because it's faster. Here is the response for the same questions above:
```json
{
  "department": {
    "probabilities": {
      "billing": 0.12924113592660363,
      "technical": 0.861768163860543,
      "sales": 0.008990700212853416
    },
    "confidence": 0.9954878538770867
  },
  "is_urgent": {
    "probabilities": {
      "yes": 0.7520748161640421,
      "no": 0.24792518383595785
    },
    "confidence": 0.9722152289381157
  }
}
```

# Step 6: Creating an HTTP API

if I want to compare this implementation to `jev` API, I need to create a similar API. I will only try to match the simple choices questions API for now.
```ts
'POST /'

type Request = {
  state: string
  model: string
  questions: Record<string, {
    type: 'choice'
    instructions: string
    criteria: Record<string, string | null>
  }>
}

type Response = {
  model: string
  answers: Record<string, {
    type: 'choice'
    choice: string
    probabilities: Record<string, number>
    confidence: number
  }>
}
```

Since I don't need routing or anything fancy, I will just use the native HTTP server API of Nodejs. And I choose to use `typia` for validation because it seems to be the fastest (even if it requires to use `ttsc` instead of `tsc` to compile the code).

After implementing the endpoint, I tested it out and the performance is very similar to before, the request is taking about **80ms**

# Step 7: News

I have the following today:

1. I can't run a benchmark against jev API and compare it with my own results, their [Master customer agreement](https://typesafe.ai/legal/mca) seems to deny it. Luckily I didn't use their API yet and will not be using it for this experiment
2. People all around the world are trying to reproduce this API and many open source attempts appeared already
3. There is a [Jev-class models](https://benchmarkheaven.com/jev-models) benchmark and leaderboard, it would be interesting to submit my solution once it's ready and see how well it will do, I don't expect much but worth trying.

So my next step will be to implement other questions types (`noul` and `score`) then check it against the public dataset of the benchmark.

# Step 8: Making the API fully compatible with `jev` API

Now my API is missing the following parts:

1. The route should be `POST /v1/systemone` instead of `POST /`
2. Handling `noul` questions
3. Handling `score` questions
4. Handling structured data in `state`, `instructions` and `criteria`
5. Returning tokens usage in the response
6. Handling more then 9 choices (numbers like `10`, `11`, ... may not fit in a single token!)

I will start by addressing point 1 to 4 that are required to run the benchmark.

**Handling `noul` questions:** 

I will implement the `noul` as a `choice` with options `Yes` and `No`.

**Handling `score` questions:**

I will also implement `score` as a `choice` by using the levels as the options then computing the weighted avergae based on the probabilities.

**Handling structured `state`, `instructions` and `criteria`**

I will just stringify the data as JSON and use it in the prompt.

# Step 9: First run of the benchmark

After implementing those improvements, it's time to run the benchmark. And since I will be running it multiple times, I created a `bench.py` script to run it and summarize the scores. Here are the scores of `minicpm5:2b-q8`:

```
Dataset          Intelligence  Calibration  Speed  Score
---------------  ------------  -----------  -----  -----
easy                     85.4         81.0   89.7   85.4
easy + standard          45.2         70.4   89.2   68.3
hard                     13.1         35.6   75.3   41.3
global                   28.8         54.1   79.9   54.3
```

There are 3 public datasets `easy` (48 tests), `standard` (72 tests) and `hard` (111 tests). `global` combines all 231 tests. Here is my simple understanding of the scores (I didn't go deeper on how they are actually computed):
- `intelligence` is how many answers are correct after correcting for random answers
- `calibration` is how much the `confidence` matches the answers
- `speed` is how fast responses are sent. Since my server is running locally, my measured times are adjusted by the benchmark to simulate a busy production server.
- `score` combines the three above into one number, with an extra penalty when intelligence is below 50

**Notes of these first results:**
- The API works correctly, there are no failures due to response structure or server errors
- This small model is very good for easy tasks
- The accuracy of the model falls down on standard and hard tasks

Overall these are good results given the simple implementation, the next step is to try some ways to improve the scores of this model and to try bigger/smarter models.

# Step 10: Benchmark updated

The [JevBench](https://benchmarkheaven.com/jev-models) is evolving quickly and has released version 1.4.2 that changed the leaderboard and details I can have about the `jev` run. I updated the `bench.py` script and README accordingly.
I have also added cost estimation based on [rental pricing on Strix halo machine](https://gpurack.net/pricing).

Then I run the benchmark against 3 models: `minicpm5-2b-q8`, `qwen3.6-35b-a3b-q6` and `qwen3.8-27b-q6`:

**minicpm5-2b-q8**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          89.6          85.4         81.0        83.2   91.4  78.1     0.0054         83.7
standard      43.1          17.3         46.0        31.7   90.9  77.5     0.0056          4.7
hard          42.3          13.1         35.5        24.3   79.6  53.6     0.0351          2.0
public        52.4          28.8         35.5        32.2   82.4  61.1     0.0197         14.6
```

**qwen3.6-35b-a3b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          97.9          97.1         89.0        93.0   81.9  56.3     0.0286         77.7
standard      77.8          67.7         73.5        70.6   82.0  55.9     0.0296         68.4
hard          51.4          26.7         42.8        34.7   68.1  35.1     0.1452          5.4
public        69.3          56.4         42.8        49.6   72.3  42.1     0.0849         36.1
```

**qwen3.8-27b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          75.0          65.1         70.0        67.5   77.0  49.3     0.0491         61.7
standard      68.1          53.6         48.0        50.8   76.6  48.4     0.0524         51.2
hard          33.3           0.0         14.3         7.1   59.7  21.7     0.4089          0.0
public        52.8          33.5         14.3        23.9   64.5  29.5     0.2230          4.2
```

The `qwen3.8` low score is due to incorrect handling on probabilities on hard questions, it returns tokens like newline and `<think>` instead of the choice numbers. I will try to fix this in the next steps.

# Step 11: Formating the prompt correctly

So far, I was sending the following raw prompt to the model:

```
{state}

---

Question: {instructions}

Choices:
  1. {choice 1 description}
  2. {choice 2 description}

Number of the correct choice:
```

The idea was that the model would autocomplete the text with the number of the correct answer and return probabilities of all answer numbers (I used the grammar to restrict the allowed output to the numbered choices).

This works but is not ideal models that were fine-tuned for chat and instructions execution rather then raw autocomplete, they expect the prompt to follow a chat format with `system`, `user` and `assistant` messages.
The `llama` API has an endpoint `/apply-template` that takes the list of messages and returns the formated prompt for the running model.
So I can use it to generate the prompt to send to `/completion`.
```js
[
  { role: 'system', content: 'Output the number of the correct choice.' },
  { role: 'user', content: /* The prompt above */ },
]
```

I should also set `enable_thinking: false` in `chat_template_kwargs` so the model doesn't return a `<think>` token.

With these changes, here are the new scores

**minicpm5-2b-q8**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          97.9          97.1         96.3        96.7   90.7  76.2     0.0062         89.2
standard      68.1          53.6         63.2        58.4   90.7  77.0     0.0059         68.4
hard          45.9          18.6         24.7        21.6   79.4  53.4     0.0357          4.4
public        63.6          47.5         24.7        36.1   82.3  60.8     0.0203         40.0
```

**qwen3.6-35b-a3b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy         100.0         100.0         99.7        99.9   81.1  54.6     0.0326         78.9
standard      91.7          87.9         92.9        90.4   81.0  54.2     0.0337         75.6
hard          71.2          56.6         78.0        67.3   67.8  34.7     0.1498         26.1
public        83.5          77.2         78.0        77.6   72.0  41.5     0.0893         43.2
```

**qwen3.8-27b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy         100.0         100.0         99.6        99.8   76.8  46.5     0.0609         63.3
standard      95.8          94.0         88.9        91.4   76.7  47.5     0.0563         64.4
hard          62.2          43.0         49.4        46.2   59.8  21.7     0.4077          5.2
public        80.5          73.9         49.4        61.6   64.7  29.4     0.2261         16.6
```

# Step 12: Fixing missing token probs and adding examples

Right now I'm using the grammar to limit the generated tokens to only the numbers of the answers but the probabilities are not limited to these tokens so sometimes the model gives probabilities for other tokens and the missing answer ends up with zero probability. One way to fix this is to increase the number of probabilities returned by the llama server.

In addition to that, and in order to help the model to generate the correct format, I added two examples before asking the question:
```js
[
  { role: 'system', content: 'Output the number of the correct choice.' },
  { role: 'user', content: 'example question 1' },
  { role: 'assistant', content: 'example answer 1' },
  { role: 'user', content: 'example question 2' },
  { role: 'assistant', content: 'example answer 2' },
  { role: 'user', content: /* The prompt above */ },
]
```

This improved the accuracy a little:

**minicpm5-2b-q8**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          97.9          97.1         96.6        96.9   90.7  77.1     0.0058         89.6
standard      66.7          51.6         48.3        50.0   90.6  76.6     0.0060         62.3
hard          48.6          22.6         23.5        23.0   79.2  53.0     0.0370          6.9
public        64.5          48.4         23.5        35.9   82.0  60.4     0.0208         40.7
```

**qwen3.6-35b-a3b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy         100.0         100.0         99.9       100.0   79.3  51.3     0.0420         76.8
standard      94.4          91.9         94.0        93.0   79.3  51.1     0.0427         74.5
hard          67.6          51.1         67.4        59.3   67.3  33.8     0.1613         23.1
public        82.7          76.5         67.4        72.0   71.0  40.1     0.0995         38.3
```

**qwen3.8-27b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy         100.0         100.0         99.9       100.0   71.9  39.6     0.1034         42.3
standard      97.2          96.0         93.3        94.6   70.9  38.7     0.1106         39.2
hard          72.1          57.9         79.0        68.4   59.0  20.5     0.4453          7.1
public        85.7          80.9         79.0        79.9   62.6  27.1     0.2699         15.0
```

# Step 13: Better estimation for the cost

So far, I was using the monthly rental price of a server with Strix halo GPU which gave me a reference cost of $0.35/hour. But looking at cloud GPU providers like [vast.ai](https://cloud.vast.ai/) I found GPUs with comparable performance to my GPU under $0.1/hour, the only caveat is that VRAM is 16GB. So if I limit the comparaison to models under 8b, I can consider the effective cost per hour to be $0.1

So I updated `bench.py` and rerun the benchmark on `minicpm5-2b-q8`
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          97.9          97.1         96.7        96.9   90.6  92.8     0.0017         94.2
standard      66.7          51.6         48.0        49.8   90.6  92.4     0.0018         64.5
hard          49.5          24.0         31.9        28.0   79.2  68.9     0.0109          9.2
public        64.9          48.9         31.9        40.4   82.1  76.3     0.0062         49.8
```

The estimated score went from `40.7` to `49.8`, because the cost no longer reduces the score.

Now, I can no longer use the big qwen models due to the 16GB constraint, so I looked for other small models:

**granite4.2-3b-q6**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy         100.0         100.0         98.4        99.2   88.4  85.6     0.0030         92.7
standard      77.8          67.7         68.5        68.1   88.4  86.6     0.0028         76.6
hard          41.4          11.8         20.6        16.2   75.3  62.5     0.0178          1.4
public        64.9          50.7         20.6        35.6   78.8  70.0     0.0100         42.0
```

**lfm2-2.6b-q8**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy         100.0         100.0         95.9        97.9   88.1  85.0     0.0032         91.9
standard      72.2          59.7         51.0        55.3   88.4  85.4     0.0031         67.3
hard          45.9          18.6         16.4        17.5   77.4  66.2     0.0134          3.9
public        65.4          50.4         16.4        33.4   80.4  72.9     0.0080         37.4
```

**ministral3-3b-q8**
```
Dataset   Accuracy  Intelligence  Calibration  Capability  Speed  Cost  $/1k est.  Score proxy
--------  --------  ------------  -----------  ----------  -----  ----  ---------  -----------
easy          97.9          97.1         96.2        96.6   90.6  91.2     0.0020         93.7
standard      84.7          77.8         70.6        74.2   89.7  90.2     0.0021         81.2
hard          46.8          19.9         62.5        41.2   75.2  62.3     0.0181          6.7
public        69.3          57.4         62.5        60.0   79.5  70.3     0.0098         66.4
```

**ministral3-3b-q8** is the champion here, even though its acurracy is comparable to other models, the good calibration scores increased its global score noticeably.

