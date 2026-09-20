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

