export type CreateChatRequest = {
    search: string,
}

export type result = {
    [key: string]: any
}

export type DialogQuestion = {
    questionId: string,
    questionText: string,
    hasChip: boolean,
    options: string[],
    questionSequence: string,
    answer: string
}
