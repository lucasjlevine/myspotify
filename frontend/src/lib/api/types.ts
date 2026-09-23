export type Play = {
  played_at: string;
  track_id: string;
  track_name: string;
  artist_names: string;
  album_name: string;
  duration_ms: number;
  context_uri: string | null;
  collected_at?: string;
};

export type AuthStatus = {
  authorized: boolean;
  expires_at?: number | null;
};

export type SyncResult = {
  fetched: number;
  inserted: number;
  skipped: number;
};

export type ModelInfo = {
  id: string;
  trained: boolean;
  artifact: string;
  trained_at?: string;
  n_plays?: number;
  n_transitions?: number;
};

export type ModelsResponse = {
  default: string;
  models: ModelInfo[];
};

export type Prediction = {
  track_id: string;
  score: number;
  track_name?: string;
  artist_names?: string;
  album_name?: string;
};

export type PredictResponse = {
  context: Play;
  model: {
    id: string;
    path: string;
    trained_at?: string | null;
    n_plays?: number | null;
    n_transitions?: number;
  };
  predictions: Prediction[];
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
};

export type TopArtist = {
  artist_names: string;
  play_count: number;
  unique_tracks: number;
};

export type HourBucket = { hour: number; play_count: number };
export type DayBucket = { day: string; play_count: number };
