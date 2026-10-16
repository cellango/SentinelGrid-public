import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { parse } from 'yaml';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const filePath = path.resolve(process.cwd(), 'cfg', 'playbooks', 'catalog.yaml');
    const raw = await fs.readFile(filePath, 'utf8');
    const parsed = parse(raw);
    return NextResponse.json(parsed ?? { playbooks: [] });
  } catch (err: any) {
    console.error('Failed to load playbooks catalog', err);
    return NextResponse.json({ playbooks: [], error: 'Failed to load catalog' }, { status: 500 });
  }
}
