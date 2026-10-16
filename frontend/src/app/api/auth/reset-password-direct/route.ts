/** The legacy direct-reset path is permanently retired. */
import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json(
    { detail: "Direct password reset has been removed. Use your identity provider's verified account recovery flow." },
    { status: 410 }
  );
}
