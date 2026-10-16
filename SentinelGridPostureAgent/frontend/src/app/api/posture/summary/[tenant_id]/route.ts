import { NextRequest, NextResponse } from 'next/server';

const POSTURE_SERVICE_URL = process.env.POSTURE_SERVICE_URL || 'http://posture-service:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { tenant_id: string } }
) {
  try {
    const { tenant_id } = params;

    const response = await fetch(
      `${POSTURE_SERVICE_URL}/api/v1/posture/summary/${tenant_id}`
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch posture summary' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Posture API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

