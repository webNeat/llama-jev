# Context

- **Hardware:** AMD Strix Halo (Ryzen AI Max+ 395) with 48GB VRAM and 48GB RAM
- **OS:** Ubuntu 25.10
- **Inference:** `llama.cpp`
- **Programming language:** Typescript, I may switch to another language if needed later

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
  - A scoring question, which in my opinion is very similar to a true/false question
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