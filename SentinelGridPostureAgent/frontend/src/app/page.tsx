import Link from 'next/link'
import { Shield, MessageSquare, BarChart3, FileSearch } from 'lucide-react'

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <div className="flex justify-center mb-6">
          <Shield className="h-20 w-20 text-primary" />
        </div>
        <h1 className="text-5xl font-bold mb-4">SentinelGrid Posture Agent</h1>
        <p className="text-xl text-muted-foreground mb-8">
          AI-powered Cloud Security Posture Management
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        <Link 
          href="/chat"
          className="group p-8 border rounded-lg hover:border-primary transition-colors"
        >
          <MessageSquare className="h-12 w-12 text-primary mb-4" />
          <h2 className="text-2xl font-semibold mb-2 group-hover:text-primary">
            AI Chat
          </h2>
          <p className="text-muted-foreground">
            Ask questions about your security posture in natural language
          </p>
        </Link>

        <Link 
          href="/posture"
          className="group p-8 border rounded-lg hover:border-primary transition-colors"
        >
          <BarChart3 className="h-12 w-12 text-primary mb-4" />
          <h2 className="text-2xl font-semibold mb-2 group-hover:text-primary">
            Posture Dashboard
          </h2>
          <p className="text-muted-foreground">
            View your security posture score and key metrics
          </p>
        </Link>

        <Link 
          href="/posture/findings"
          className="group p-8 border rounded-lg hover:border-primary transition-colors"
        >
          <FileSearch className="h-12 w-12 text-primary mb-4" />
          <h2 className="text-2xl font-semibold mb-2 group-hover:text-primary">
            Findings
          </h2>
          <p className="text-muted-foreground">
            Browse and manage security findings from scans
          </p>
        </Link>
      </div>

      <div className="text-center mt-16 text-sm text-muted-foreground">
        <p>Powered by SentinelGrid | MCP Protocol Enabled</p>
      </div>
    </div>
  )
}

