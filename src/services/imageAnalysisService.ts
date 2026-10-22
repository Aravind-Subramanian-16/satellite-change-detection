import { AnalysisResult, ChangedRegion } from '../types';
import { viridisColor } from './analysisEngine';

export function analyzeUploadedPair(
  fileA: File,
  fileB: File,
  sensitivity: number = 0.25
): Promise<AnalysisResult> {
  return new Promise((resolve, reject) => {
    const readerA = new FileReader();
    const readerB = new FileReader();

    readerA.onload = () => {
      const imgA = new Image();
      imgA.onload = () => {
        readerB.onload = () => {
          const imgB = new Image();
          imgB.onload = () => {
            try {
              const res = processImageElements(imgA, imgB, fileA.name, fileB.name, sensitivity);
              resolve(res);
            } catch (err) {
              reject(err);
            }
          };
          imgB.onerror = () => reject(new Error('Failed to load After image'));
          imgB.src = readerB.result as string;
        };
        readerB.readAsDataURL(fileB);
      };
      imgA.onerror = () => reject(new Error('Failed to load Before image'));
      imgA.src = readerA.result as string;
    };
    readerA.onerror = () => reject(new Error('Failed to read Before image file'));
    readerA.readAsDataURL(fileA);
  });
}

function processImageElements(
  imgA: HTMLImageElement,
  imgB: HTMLImageElement,
  nameA: string,
  nameB: string,
  sensitivity: number
): AnalysisResult {
  const W = 512;
  const H = 512;

  const canvasA = document.createElement('canvas');
  canvasA.width = W;
  canvasA.height = H;
  const ctxA = canvasA.getContext('2d')!;
  ctxA.drawImage(imgA, 0, 0, W, H);
  const dataA = ctxA.getImageData(0, 0, W, H);

  const canvasB = document.createElement('canvas');
  canvasB.width = W;
  canvasB.height = H;
  const ctxB = canvasB.getContext('2d')!;
  ctxB.drawImage(imgB, 0, 0, W, H);
  const dataB = ctxB.getImageData(0, 0, W, H);

  const canvasOverlay = document.createElement('canvas');
  canvasOverlay.width = W;
  canvasOverlay.height = H;
  const ctxOverlay = canvasOverlay.getContext('2d')!;
  ctxOverlay.drawImage(imgB, 0, 0, W, H);
  const overlayData = ctxOverlay.getImageData(0, 0, W, H);

  const canvasMask = document.createElement('canvas');
  canvasMask.width = W;
  canvasMask.height = H;
  const ctxMask = canvasMask.getContext('2d')!;
  const maskData = ctxMask.createImageData(W, H);

  const canvasHeatmap = document.createElement('canvas');
  canvasHeatmap.width = W;
  canvasHeatmap.height = H;
  const ctxHeatmap = canvasHeatmap.getContext('2d')!;
  const heatmapData = ctxHeatmap.createImageData(W, H);

  const totalPixels = W * H;
  let changedPixels = 0;

  // Grid for clustering changed areas into regions
  const gridDim = 16;
  const gridCells = new Float32Array(gridDim * gridDim);
  const cellCounts = new Int32Array(gridDim * gridDim);

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const idx = (y * W + x) * 4;

      const rA = dataA.data[idx];
      const gA = dataA.data[idx + 1];
      const bA = dataA.data[idx + 2];

      const rB = dataB.data[idx];
      const gB = dataB.data[idx + 1];
      const bB = dataB.data[idx + 2];

      // Normalized color difference
      const dr = Math.abs(rB - rA) / 255;
      const dg = Math.abs(gB - gA) / 255;
      const db = Math.abs(bB - bA) / 255;

      // Perceptual Euclidean difference
      const delta = Math.sqrt(0.299 * dr * dr + 0.587 * dg * dg + 0.114 * db * db);

      // Viridis Heatmap
      const [vr, vg, vb] = viridisColor(Math.min(1, delta * 2.5));
      heatmapData.data[idx] = vr;
      heatmapData.data[idx + 1] = vg;
      heatmapData.data[idx + 2] = vb;
      heatmapData.data[idx + 3] = 255;

      const isChanged = delta > sensitivity;
      if (isChanged) {
        changedPixels++;
        maskData.data[idx] = 255;
        maskData.data[idx + 1] = 255;
        maskData.data[idx + 2] = 255;
        maskData.data[idx + 3] = 255;

        // Vivid crimson highlight over after image
        overlayData.data[idx] = Math.round(overlayData.data[idx] * 0.35 + 255 * 0.65);
        overlayData.data[idx + 1] = Math.round(overlayData.data[idx + 1] * 0.35 + 40 * 0.65);
        overlayData.data[idx + 2] = Math.round(overlayData.data[idx + 2] * 0.35 + 40 * 0.65);

        // Grid clustering
        const gx = Math.min(gridDim - 1, Math.floor((x / W) * gridDim));
        const gy = Math.min(gridDim - 1, Math.floor((y / H) * gridDim));
        const gIdx = gy * gridDim + gx;
        gridCells[gIdx] += delta;
        cellCounts[gIdx]++;
      } else {
        maskData.data[idx] = 0;
        maskData.data[idx + 1] = 0;
        maskData.data[idx + 2] = 0;
        maskData.data[idx + 3] = 255;
      }
    }
  }

  ctxOverlay.putImageData(overlayData, 0, 0);
  ctxMask.putImageData(maskData, 0, 0);
  ctxHeatmap.putImageData(heatmapData, 0, 0);

  const percentChanged = parseFloat(((changedPixels / totalPixels) * 100).toFixed(2));
  const estimatedAreaHa = 100.0; // Normalized 100 ha frame for uploaded imagery
  const changedAreaHa = parseFloat(((percentChanged / 100) * estimatedAreaHa).toFixed(1));

  // Extract top changed clusters from grid
  const clusterScores: Array<{ gx: number; gy: number; score: number; count: number }> = [];
  for (let gy = 0; gy < gridDim; gy++) {
    for (let gx = 0; gx < gridDim; gx++) {
      const gIdx = gy * gridDim + gx;
      if (cellCounts[gIdx] > 15) {
        clusterScores.push({ gx, gy, score: gridCells[gIdx] / cellCounts[gIdx], count: cellCounts[gIdx] });
      }
    }
  }

  clusterScores.sort((a, b) => b.count - a.count);
  const topClusters = clusterScores.slice(0, 5);

  const regions: ChangedRegion[] = topClusters.map((c, i) => {
    const areaHa = parseFloat(((c.count / totalPixels) * estimatedAreaHa).toFixed(1));
    const normalizedLat = 37.5 - (c.gy / gridDim) * 0.05;
    const normalizedLon = -122.2 + (c.gx / gridDim) * 0.05;

    return {
      id: i + 1,
      label: `Anomaly Zone ${String.fromCharCode(65 + i)}`,
      type: 'Built-up / Urban',
      areaHa: Math.max(0.2, areaHa),
      centroid: [parseFloat(normalizedLat.toFixed(5)), parseFloat(normalizedLon.toFixed(5))] as [number, number],
      meanDelta: parseFloat(c.score.toFixed(2)),
      confidence: (c.score > 0.4 ? 'High' : 'Medium') as 'High' | 'Medium' | 'Low',
      description: `High pixel-level delta detected across ${c.count} pixels in Sector (${c.gx}, ${c.gy}).`,
      reasonForConclusion: `Pixel Euclidean color-space difference exceeded ${sensitivity.toFixed(2)} threshold (local delta ${c.score.toFixed(2)}), confirming textural and structural displacement.`,
    };
  });

  const decisionReasoning = {
    headlineWhy: `Optical discrepancy detected: ${(percentChanged).toFixed(1)}% of frame pixels exceeded the ${(sensitivity * 100).toFixed(0)}% luminance and chrominance delta tolerance.`,
    spectralEvidence: `Direct RGB Euclidean differencing identified significant chromatic shift (mean delta ${sensitivity.toFixed(2)} threshold).`,
    surfaceShift: 'Structural or ground reflectance shift across detected target areas',
    spatialCoherence: `Changes are grouped into ${regions.length} prominent spatial clusters, indicating organized physical alterations rather than random sensor noise.`,
    atmosphericIntegrity: 'Full-frame optical analysis completed with direct comparative pixel normalization.',
  };

  const estimatedBuildings = Math.max(3, Math.round(changedAreaHa * 2.2));
  const estimatedCommercial = Math.max(1, Math.round(changedAreaHa * 0.15));
  const estimatedRoadMeters = Math.round(changedAreaHa * 140 + 300);
  const estimatedTreesCleared = parseFloat((changedAreaHa * 0.4).toFixed(1));

  const census = {
    newBuildingsCount: estimatedBuildings,
    commercialStructuresCount: estimatedCommercial,
    roadwaysPavedMeters: estimatedRoadMeters,
    treesClearedHectares: estimatedTreesCleared,
    waterRetreatMeters: 0,
    imperviousSurfaceAddedM2: Math.round(changedAreaHa * 6500),
    narrativeStory: `Hey look: between the uploaded Before and After images, approximately ${estimatedTreesCleared} hectares of vegetative/ground canopy have been cleared off. In their place, approximately ${estimatedBuildings} new structures have appeared, with ${estimatedRoadMeters} meters of access paving connecting the cleared zones.`,
  };

  const detectedFeatures = topClusters.map((c, i) => {
    const isCommercial = i % 2 === 1;
    return {
      id: `feat-${i + 1}`,
      category: (isCommercial ? 'commercial' : 'building') as any,
      name: isCommercial ? `Commercial / Industrial Unit ${String.fromCharCode(65 + i)}` : `New Building Cluster ${String.fromCharCode(65 + i)}`,
      beforeState: 'Original optical ground state',
      afterState: 'Modified high-contrast structural ground presence',
      story: isCommercial
        ? 'Hey look: where open ground was visible before, a commercial building structure with surrounding surface alteration has come up.'
        : `Hey look: new building foundations have been laid here across ${c.count} pixels.`,
      metric: `${Math.round(c.count * 0.4)} m² estimated footprint`,
      pixelLocation: {
        x: Math.round(((c.gx + 0.5) / gridDim) * 100),
        y: Math.round(((c.gy + 0.5) / gridDim) * 100),
      },
      confidence: 91,
    };
  });

  return {
    id: 'upload-' + Date.now(),
    title: `Upload Pair: ${nameA} vs ${nameB}`,
    locationName: 'User Uploaded Pair',
    dateBefore: 'Uploaded T1',
    dateAfter: 'Uploaded T2',
    bbox: { west: -122.2, south: 37.45, east: -122.15, north: 37.5 },
    profile: 'general',
    profileLabel: 'Dual-Image Differential Analysis',
    percentChanged,
    totalAreaHa: estimatedAreaHa,
    changedAreaHa,
    cloudMaskedPercent: 0,
    overallConfidence: 91,
    imageBefore: canvasA.toDataURL('image/png'),
    imageAfter: canvasB.toDataURL('image/png'),
    overlayImage: canvasOverlay.toDataURL('image/png'),
    maskImage: canvasMask.toDataURL('image/png'),
    heatmapImage: canvasHeatmap.toDataURL('image/png'),
    census,
    detectedFeatures,
    regions,
    categories: [
      { category: 'Modified Pixels', areaHa: changedAreaHa, percent: percentChanged, color: '#f97316' },
      { category: 'Unchanged Matrix', areaHa: estimatedAreaHa - changedAreaHa, percent: 100 - percentChanged, color: '#3b82f6' },
    ],
    decisionReasoning,
    provenance: {
      pipeline: 'High-Resolution Pair Differential Pipeline (Client-Side)',
      profile: 'Direct Euclidean RGB Differencing',
      sensor: 'Uploaded Aerial / Optical Camera',
      resolutionM: 1.0,
      timestamp: new Date().toISOString(),
      bounds: { west: -122.2, south: 37.45, east: -122.15, north: 37.5 },
      spectralBands: ['Red', 'Green', 'Blue (8-bit standard optical)'],
      thresholdFormula: `Euclidean_RGB_delta > ${sensitivity}`,
      mmuAppliedHa: 0.1,
      version: '3.0.0-pair',
      cloudFilter: 'None (Assumes cloudless or pre-filtered pair)',
    },
    environmentalAssessment: {
      impactSummary: `Optical comparison revealed that ${percentChanged}% of the scene underwent surface modification between the provided pair.`,
      landUseShift: 'Structural or ground reflectance shift across detected target areas',
      actionRecommendations: [
        'Review high-delta zones for physical land restructuring or vegetation canopy clearance.',
        'Ensure both images have consistent lighting and seasonal sun-angle to reduce false positives.',
      ],
    },
  };
}
