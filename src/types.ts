export type Request = {
  model: string
  state: unknown
  questions: Record<string, Question>
}

export type Response = {
  model: string
  answers: Record<string, Answer>
  usage: {
    input_tokens: number
    output_tokens: number
  }
}

export type Question = ChoiceQuestion | NoulQuestion | ScoreQuestion

export type ChoiceQuestion = {
  type: 'choice'
  instructions: unknown
  criteria: Record<string, unknown>
}

export type NoulQuestion = {
  type: 'noul'
  instructions: unknown
  criteria?: { true: unknown; false: unknown }
}

export type ScoreQuestion = {
  type: 'score'
  instructions: unknown
  criteria: unknown[]
}

export type Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer

export type NoulAnswer = {
  type: 'noul'
  noul: number
}

export type ChoiceAnswer = {
  type: 'choice'
  choice: string
  probabilities: Record<string, number>
  confidence: number
}

export type ScoreAnswer = {
  type: 'score'
  score: number
  legend: Record<string, unknown>
  probabilities: Record<string, number>
  confidence: number
}
