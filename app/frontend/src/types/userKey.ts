// BYO API keys — user-supplied provider credentials.

export type Provider = 'gemini' | 'fal' | 'kling'

export interface UserKey {
  provider: Provider
  last_four: string
  validated_at: string | null
}

export interface UserKeysResponse {
  keys: UserKey[]
}
