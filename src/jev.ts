import { Answer, Question, Request, Response } from './types.js'

export async function jev({ model, state, questions }: Request): Promise<Response> {
  const entries = Object.entries(questions)
  const results = await Promise.all(entries.map(([_, question]) => jev_answer(state, question)))
  const res: Response = { model, answers: {} }
  for (let i = 0; i < entries.length; i++) {
    const [name] = entries[i]!
    res.answers[name] = results[i]!
  }
  return res
}

async function jev_answer(state: string, question: Question) {
  question.criteria['not sure'] = 'I am not confident'
  const prompt = [state, `\n---\n`, `Question: ${question.instructions}\n`, `Choices:`]
  const choices = Object.entries(question.criteria)
  const next_tokens: string[] = []
  let n = 1
  for (const [choice, description] of choices) {
    prompt.push(`  ${n}. ${choice}${description ? ': ' + description : ''}`)
    next_tokens.push(String(n))
    n += 1
  }
  prompt.push(`\nNumber of the correct choice: `)
  const probs = await next_token_probs(prompt.join(`\n`), next_tokens)
  const answer: Answer = {
    type: 'choice',
    choice: choices[0][0],
    probabilities: {},
    confidence: 0,
  }
  let top_i = 0
  let total_probs = 0
  for (let i = 0; i < choices.length; i++) {
    const n = i + 1
    const [choice] = choices[i]!
    if (choice === 'not sure') answer.confidence = 1 - probs[n]!
    else {
      answer.probabilities[choice] = probs[n]
      total_probs += probs[n]!
      if (probs[n] > probs[top_i]) {
        top_i = n
        answer.choice = choice
      }
    }
  }
  for (const name of Object.keys(answer.probabilities)) {
    answer.probabilities[name]! /= total_probs
  }
  return answer
}

async function next_token_probs(prompt: string, tokens: string[]) {
  const grammar = `root ::= ${tokens.map((x) => `"${x}"`).join('|')}`
  const res = await fetch('http://localhost:8080/completion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, n_predict: 1, n_probs: tokens.length, grammar }),
  })
  const data: any = await res.json()
  const probs: Record<string, number> = {}
  for (const { token, logprob } of data.completion_probabilities[0].top_logprobs) {
    probs[token] = Math.exp(logprob)
  }
  return probs
}
