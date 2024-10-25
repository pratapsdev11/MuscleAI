import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { UploadForm } from "@/components/upload-form"
import { LiveStreamForm } from "@/components/live-stream-form"

export default function Home() {
  return (
    <div className="container py-8">
      <div className="flex flex-col items-center justify-center space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tighter">
            Professional Fitness Analysis Platform
          </h1>
          <p className="text-muted-foreground max-w-[600px]">
            Upload your workout videos or start a live session for real-time form analysis
            and injury prevention insights.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-5xl">
          <Card>
            <CardHeader>
              <CardTitle>Video Analysis</CardTitle>
              <CardDescription>
                Upload your workout video for detailed form analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <UploadForm />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Live Analysis</CardTitle>
              <CardDescription>
                Start a live session for real-time feedback
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LiveStreamForm />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

