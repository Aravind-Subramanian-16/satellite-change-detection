export interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export type ProfileKey =
  | 'general'
  | 'urban'
  | 'vegetation'
  | 'agriculture'
  | 'water'
  | 'roads';

export interface ProfileInfo {
  key: ProfileKey;
  label: string;
  description: string;
  indices: string[];
  defaultMmuHa: number;
  useCase: string;
  thresholds: Record<string, number>;
}

export interface PresetLocation {
  id: string;
  name: string;
  subtitle: string;
  tag: string;
  bbox: BoundingBox;
  dateBefore: string;
  dateAfter: string;
  profile: ProfileKey;
  description: string;
}

export interface CandidateScene {
  id: string;
  date: string;
  cloudCover: number;
  aoiCoverage: number;
  recommended: boolean;
  satellite: string;
  thumbnailUrl?: string;
}

export interface DetectedFeature {
  id: string;
  category: 'building' | 'road' | 'cleared_trees' | 'water_loss' | 'commercial';
  name: string;
  beforeState: string;
  afterState: string;
  story: string;
  metric: string;
  pixelLocation: { x: number; y: number }; // Percentage (0-100) on image for pin overlays
  confidence: number;
}

export interface PreciseCensus {
  newBuildingsCount: number;
  commercialStructuresCount: number;
  roadwaysPavedMeters: number;
  treesClearedHectares: number;
  waterRetreatMeters: number;
  imperviousSurfaceAddedM2: number;
  narrativeStory: string;
}

export interface ChangedRegion {
  id: number;
  label: string;
  type: 'Built-up / Urban' | 'Vegetation Loss' | 'Water Dynamics' | 'Bare Soil' | 'Infrastructure';
  areaHa: number;
  centroid: [number, number]; // [lat, lon]
  meanDelta: number;
  confidence: 'High' | 'Medium' | 'Low';
  bbox?: [number, number, number, number]; // [w, s, e, n]
  description: string;
  reasonForConclusion: string;
}

export interface CategoryBreakdown {
  category: string;
  areaHa: number;
  percent: number;
  color: string;
}

export interface AnalysisProvenance {
  pipeline: string;
  profile: string;
  sensor: string;
  resolutionM: number;
  timestamp: string;
  bounds: BoundingBox;
  spectralBands: string[];
  thresholdFormula: string;
  mmuAppliedHa: number;
  version: string;
  cloudFilter: string;
}

export interface DecisionReasoning {
  headlineWhy: string;
  spectralEvidence: string;
  surfaceShift: string;
  spatialCoherence: string;
  atmosphericIntegrity: string;
}

export interface GeospatialAccuracyMetrics {
  precision: number;
  recall: number;
  f1Score: number;
  iouScore: number;
  kappaCoefficient: number;
  trainingSamplesCount: number;
  terrainSignature: string;
  soilModelApplied: string;
  cadastralAccuracy: string;
}

export interface AnalysisResult {
  id: string;
  title: string;
  locationName: string;
  dateBefore: string;
  dateAfter: string;
  bbox: BoundingBox;
  profile: ProfileKey;
  profileLabel: string;
  percentChanged: number;
  totalAreaHa: number;
  changedAreaHa: number;
  cloudMaskedPercent: number;
  overallConfidence: number; // 0-100
  imageBefore: string; // data URL or path
  imageAfter: string;
  overlayImage: string;
  maskImage: string;
  heatmapImage: string;
  census: PreciseCensus; // Precise counts: buildings added, roads paved, trees cleared
  detectedFeatures: DetectedFeature[]; // Exact pinpointable objects on image
  regions: ChangedRegion[];
  categories: CategoryBreakdown[];
  decisionReasoning: DecisionReasoning;
  provenance: AnalysisProvenance;
  accuracyMetrics?: GeospatialAccuracyMetrics;
  environmentalAssessment: {
    impactSummary: string;
    biomassLossEstimateTons?: number;
    imperviousSurfaceGainHa?: number;
    waterVolumeDeltaM3?: number;
    landUseShift: string;
    actionRecommendations: string[];
  };
  imagerySource?: {
    beforeProvider: string;
    afterProvider: string;
    resolutionM: number;
    isRealSatellite: boolean;
    width: number;
    height: number;
  };
  warnings?: string[];
}

export interface HistoryItem {
  id: string;
  title: string;
  dateCreated: string;
  dateBefore: string;
  dateAfter: string;
  locationName: string;
  percentChanged: number;
  profile: ProfileKey;
  thumbnail: string;
  result: AnalysisResult;
}

export interface AutoFillPayload {
  action: 'AUTO_FILL_ANALYSIS';
  locationName: string;
  approxLat: number;
  approxLon: number;
  dateBefore: string;
  dateAfter: string;
  profile: ProfileKey;
  autoRun?: boolean;
  explanation?: string;
  bbox?: BoundingBox;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
  timestamp: string;
  actionPayload?: AutoFillPayload;
}

export type DetectionEngineKey =
  | 'fusion_sota'
  | 'spectral_physics'
  | 'cadastral_highres';

export interface EngineConfigInfo {
  key: DetectionEngineKey;
  name: string;
  badge: string;
  description: string;
  precision: number;
  recall: number;
  f1Score: number;
  iouScore: number;
  recommendedFor: string;
}

