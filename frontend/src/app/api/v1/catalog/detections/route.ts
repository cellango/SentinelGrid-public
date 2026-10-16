import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { parse } from 'yaml';

// Always read from the mounted catalog at request-time (no build-time caching)
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const filePath = path.resolve(process.cwd(), 'cfg', 'detections', 'catalog.yaml');
    const raw = await fs.readFile(filePath, 'utf8');
    const parsed = parse(raw);
    return NextResponse.json(parsed ?? { detections: [] });
  } catch (err: any) {
    console.error('Failed to load detections catalog', err);
    return NextResponse.json({ detections: [], error: 'Failed to load catalog' }, { status: 500 });
  }
}
