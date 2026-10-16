import { NextRequest, NextResponse } from 'next/server';

const MCP_URL = process.env.MCP_URL || 'http://posture-mcp-server:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { tool, arguments: args } = body;

    // Forward to MCP server
    // Note: In production, this would use the MCP protocol over stdio
    // For now, we'll make a simple HTTP call to the MCP server's API
    
    const response = await fetch(`${MCP_URL}/api/mcp/call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tool,
        arguments: args,
      }),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'MCP call failed' },
        { status: response.status }
      );
    }

    const result = await response.json();
    return NextResponse.json({ result });
  } catch (error) {
    console.error('MCP API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

