import { AnalysisResult, NormalizedRegion } from '../types';
import { viridisColor } from './analysisEngine';

const MAX_ANALYSIS_DIMENSION = 2048;

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`Could not decode image: ${file.name}`));
    };
    image.src = url;
  });
}

function createCanvas(width: number, height: number): {
  canvas: HTMLCanvasElement;
  context: CanvasRenderingContext2D;
} {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  if (!context) throw new Error('This browser could not create an image analysis canvas.');
  return { canvas, context };
}

function getCrop(image: HTMLImageElement, region: NormalizedRegion) {
  const left = Math.round(region.x * image.naturalWidth);
  const top = Math.round(region.y * image.naturalHeight);
  const width = Math.round(region.width * image.naturalWidth);
  const height = Math.round(region.height * image.naturalHeight);
  return {
    left,
    top,
    width: Math.min(width, image.naturalWidth - left),
    height: Math.min(height, image.naturalHeight - top),
  };
}

export async function analyzeUploadedPair(
  fileA: File,
  fileB: File,
  sensitivity = 0.25,
  selectedRegion: NormalizedRegion = { x: 0, y: 0, width: 1, height: 1 }
): Promise<AnalysisResult> {
  const region = selectedRegion;
  if (
    !Number.isFinite(region.x) ||
    !Number.isFinite(region.y) ||
    !Number.isFinite(region.width) ||
    !Number.isFinite(region.height) ||
    region.x < 0 ||
    region.y < 0 ||
    region.width <= 0 ||
    region.height <= 0 ||
    region.x + region.width > 1 ||
    region.y + region.height > 1
  ) {
    throw new Error('Select a valid matching region inside both images.');
  }

  const [imgA, imgB] = await Promise.all([loadImage(fileA), loadImage(fileB)]);
  const cropA = getCrop(imgA, region);
  const cropB = getCrop(imgB, region);
  if (cropA.width < 64 || cropA.height < 64 || cropB.width < 64 || cropB.height < 64) {
    throw new Error('The selected region is too small. Choose an area at least 64 × 64 pixels in both images.');
  }

  const aspectA = cropA.width / cropA.height;
  const aspectB = cropB.width / cropB.height;
  if (Math.abs(aspectA - aspectB) / Math.max(aspectA, aspectB) > 0.02) {
    throw new Error('The images have different aspect ratios. Align/crop them to the same footprint before comparing.');
  }

  // Use the lower-resolution crop as the common grid and cap work for browser responsiveness.
  const width = Math.min(cropA.width, cropB.width, MAX_ANALYSIS_DIMENSION);
  const height = Math.min(cropA.height, cropB.height, MAX_ANALYSIS_DIMENSION);

  const before = createCanvas(width, height);
  const after = createCanvas(width, height);
  before.context.imageSmoothingEnabled = true;
  after.context.imageSmoothingEnabled = true;
  before.context.drawImage(imgA, cropA.left, cropA.top, cropA.width, cropA.height, 0, 0, width, height);
  after.context.drawImage(imgB, cropB.left, cropB.top, cropB.width, cropB.height, 0, 0, width, height);

  const beforeData = before.context.getImageData(0, 0, width, height);
  const afterData = after.context.getImageData(0, 0, width, height);
  const overlay = createCanvas(width, height);
  const mask = createCanvas(width, height);
  const heatmap = createCanvas(width, height);
  overlay.context.drawImage(after.canvas, 0, 0);
  const overlayData = overlay.context.getImageData(0, 0, width, height);
  const maskData = mask.context.createImageData(width, height);
  const heatmapData = heatmap.context.createImageData(width, height);
  const totalPixels = width * height;
  let changedPixels = 0;

  for (let pixel = 0; pixel < totalPixels; pixel++) {
    const index = pixel * 4;
    const dr = (afterData.data[index] - beforeData.data[index]) / 255;
    const dg = (afterData.data[index + 1] - beforeData.data[index + 1]) / 255;
    const db = (afterData.data[index + 2] - beforeData.data[index + 2]) / 255;
    const delta = Math.sqrt(0.299 * dr * dr + 0.587 * dg * dg + 0.114 * db * db);
    const [red, green, blue] = viridisColor(Math.min(1, delta * 2.5));
    heatmapData.data[index] = red;
    heatmapData.data[index + 1] = green;
    heatmapData.data[index + 2] = blue;
    heatmapData.data[index + 3] = 255;

    const changed = delta > sensitivity;
    if (changed) {
      changedPixels++;
      maskData.data[index] = 255;
      maskData.data[index + 1] = 255;
      maskData.data[index + 2] = 255;
      overlayData.data[index] = Math.round(overlayData.data[index] * 0.35 + 255 * 0.65);
      overlayData.data[index + 1] = Math.round(overlayData.data[index + 1] * 0.35 + 40 * 0.65);
      overlayData.data[index + 2] = Math.round(overlayData.data[index + 2] * 0.35 + 40 * 0.65);
    }
    maskData.data[index + 3] = 255;
  }

  overlay.context.putImageData(overlayData, 0, 0);
  mask.context.putImageData(maskData, 0, 0);
  heatmap.context.putImageData(heatmapData, 0, 0);

  const percentChanged = Number(((changedPixels / totalPixels) * 100).toFixed(2));
  const changedPixelShare = changedPixels.toLocaleString();
  const warnings = [
    'This is an RGB pixel-difference screen, not a validated land-cover or object detector. A flagged pixel is not proof of a physical change.',
    'The images are compared at matching normalized coordinates; no image registration or illumination/season correction is performed. Misalignment, shadows, haze, and exposure differences can create false detections.',
    'The uploaded images have no geospatial scale/coordinates in this workflow. Hectares, metres, geographic coordinates, and accuracy/confidence scores are not reported.',
    'For scientific interpretation, use co-registered imagery from comparable dates and verify candidate areas against independent data or field observations.',
  ];

  return {
    analysisMode: 'uploaded-rgb-screening',
    analysisPixelStats: {
      width,
      height,
      totalPixels,
      changedPixels,
      selectedRegion: region,
    },
    id: `upload-${Date.now()}`,
    title: `RGB screen: ${fileA.name} vs ${fileB.name}`,
    locationName: 'User Uploaded Pair',
    dateBefore: 'Uploaded T1',
    dateAfter: 'Uploaded T2',
    bbox: { west: 0, south: 0, east: 0, north: 0 },
    profile: 'general',
    profileLabel: 'RGB pixel-difference screening',
    percentChanged,
    totalAreaHa: 0,
    changedAreaHa: 0,
    cloudMaskedPercent: 0,
    imageBefore: before.canvas.toDataURL('image/png'),
    imageAfter: after.canvas.toDataURL('image/png'),
    overlayImage: overlay.canvas.toDataURL('image/png'),
    maskImage: mask.canvas.toDataURL('image/png'),
    heatmapImage: heatmap.canvas.toDataURL('image/png'),
    census: {
      newBuildingsCount: 0,
      commercialStructuresCount: 0,
      roadwaysPavedMeters: 0,
      treesClearedHectares: 0,
      waterRetreatMeters: 0,
      imperviousSurfaceAddedM2: 0,
      narrativeStory: `${percentChanged}% of pixels (${changedPixelShare} of ${totalPixels.toLocaleString()}) in the selected region exceeded the RGB difference threshold (${sensitivity.toFixed(2)}). This is a visual screening signal only; it does not identify the type or cause of change.`,
    },
    detectedFeatures: [],
    regions: [],
    categories: [],
    decisionReasoning: {
      headlineWhy: `${percentChanged}% of selected-region pixels exceeded the normalized RGB difference threshold of ${sensitivity.toFixed(2)}.`,
      spectralEvidence: 'Only 8-bit RGB channel differences were measured. No near-infrared, shortwave-infrared, or other spectral bands were available.',
      surfaceShift: 'Surface type and cause are not classified by this screening step.',
      spatialCoherence: 'No object segmentation, georeferencing, or minimum mapping unit was applied.',
      atmosphericIntegrity: 'Cloud, shadow, seasonal, sensor, and illumination effects were not corrected.',
    },
    provenance: {
      pipeline: 'Client-side RGB pixel-difference screening',
      profile: 'RGB only; no semantic classifier',
      sensor: `User-provided images (${imgA.naturalWidth} × ${imgA.naturalHeight}; ${imgB.naturalWidth} × ${imgB.naturalHeight} px)`,
      resolutionM: 0,
      timestamp: new Date().toISOString(),
      bounds: { west: 0, south: 0, east: 0, north: 0 },
      spectralBands: ['Red', 'Green', 'Blue (8-bit)'],
      thresholdFormula: `Weighted RGB difference > ${sensitivity.toFixed(2)} (normalized 0–1)`,
      mmuAppliedHa: 0,
      version: '4.0.0-rgb-screen',
      cloudFilter: 'Not available for uploaded RGB images',
    },
    imagerySource: {
      beforeProvider: `Uploaded: ${fileA.name}`,
      afterProvider: `Uploaded: ${fileB.name}`,
      resolutionM: 0,
      isRealSatellite: false,
      width,
      height,
    },
    warnings,
    environmentalAssessment: {
      impactSummary: `${percentChanged}% of the selected image region exceeded the RGB difference threshold. No land-cover or environmental impact class was inferred.`,
      landUseShift: 'Not classified from RGB difference alone',
      actionRecommendations: [
        'Inspect the overlay and verify flagged areas against the source images.',
        'For area estimates or land-cover conclusions, provide georeferenced imagery with known ground resolution and use a validated, task-specific method.',
      ],
    },
  };
}
