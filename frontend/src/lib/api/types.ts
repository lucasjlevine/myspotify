export type Play = {
  played_at: string;
  track_id: string;
  track_name: string;
  artist_names: string;
  album_name: string;
  duration_ms: number;
  context_uri: string | null;
  collected_at?: string;
  album_image_url?: string | null;
};

export type AuthStatus = {
  authorized: boolean;
  expires_at?: number | null;
};

export type SyncResult = {
  fetched: number;
  inserted: number;
  skipped: number;
  images_updated?: number;
};

export type ModelInfo = {
  id: string;
  trained: boolean;
  artifact: string;
  trained_at?: string;
  n_plays?: number;
  n_transitions?: number;
  n_tracks?: number;
  backend?: string;
  dim?: number;
  model_name?: string;
};

export type WindowPreset = {
  id: string;
  label: string;
  description: string;
};

export type ModelsResponse = {
  default: string;
  models: ModelInfo[];
  windows?: WindowPreset[];
};

export type Prediction = {
  track_id: string;
  score: number;
  track_name?: string;
  artist_names?: string;
  album_name?: string;
  album_image_url?: string | null;
};

export type PredictResponse = {
  context: Play;
  seeds?: Play[];
  window?: string;
  model: {
    id: string;
    path: string;
    trained_at?: string | null;
    n_plays?: number | null;
    n_transitions?: number;
    backend?: string;
  };
  predictions: Prediction[];
};

export type PromptSearchResponse = {
  query: string;
  model: {
    id: string;
    path: string;
    backend?: string | null;
    model_name?: string | null;
    trained_at?: string | null;
    n_tracks?: number | null;
    dim?: number | null;
  };
  predictions: Prediction[];
};

export type SpacePoint = {
  id: string;
  kind: "query" | "neighbor" | "context";
  x: number;
  y: number;
  score?: number;
  label?: string;
  annotated?: boolean;
  track_id?: string;
  track_name?: string;
  artist_names?: string;
  album_name?: string;
  album_image_url?: string | null;
};

export type SpaceEdge = {
  source: string;
  target: string;
  weight: number;
  kind: string;
};

export type SpaceResponse = {
  query: string;
  model: PromptSearchResponse["model"] & { text_dim?: number | null };
  points: SpacePoint[];
  edges: SpaceEdge[];
};

export type StatsSummary = {
  total_plays: number;
  unique_tracks: number;
  unique_artists: number;
  first_played_at: string | null;
  last_played_at: string | null;
  total_ms: number;
};

export type TopTrack = {
  track_id: string;
  track_name: string;
  artist_names: string;
  album_name: string;
  play_count: number;
  raw_play_count?: number;
  album_image_url?: string | null;
  total_ms?: number;
  last_played_at?: string | null;
  time_range?: string;
  daily_cap?: number;
};

export type TopArtist = {
  artist_names: string;
  play_count: number;
  raw_play_count?: number;
  unique_tracks: number;
  total_ms?: number;
  last_played_at?: string | null;
  album_image_url?: string | null;
  time_range?: string;
  daily_cap?: number;
};

export type HourBucket = { hour: number; play_count: number };
export type DayBucket = { day: string; play_count: number };
