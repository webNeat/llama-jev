async function next_token_probs(prompt: string, n_probs: number) {
  const res = await fetch('http://localhost:8080/completion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, n_predict: 1, n_probs }),
  })
  const data: any = await res.json()
  const probs: Record<string, number> = {}
  for (const { token, logprob } of data.completion_probabilities[0].top_logprobs) {
    probs[token] = Math.exp(logprob)
  }
  return probs
}

for (let i = 0; i < 5; i++) {
  const start = performance.now()
  await next_token_probs(`Question: Who discovered the theory of relativity. Answer:`, 5)
  const duration = performance.now() - start
  console.log(Math.floor(duration) + 'ms')
}
