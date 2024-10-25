import { Separator } from "@/components/ui/separator"
import { Dumbbell } from "lucide-react"
import { FC } from "react"
import DeveloperCard from "./developer-card"
import { developers } from "@/data/dev"

export const Footer: FC = () => {
  const currentYear: number = new Date().getFullYear()
  
  return (
    <footer className="w-full border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container py-8 md:py-12">
        <div className="flex flex-col items-center space-y-8">
          <div className="flex items-center space-x-2 text-primary">
            <Dumbbell className="h-6 w-6" />
            <span className="text-xl font-semibold">JIM</span>
          </div>
          
          <div className="flex flex-wrap justify-center gap-6 w-full max-w-2xl">
            {developers.map((developer) => (
              <DeveloperCard
                key={developer.githubUsername}
                {...developer}
                className="flex-shrink-0 w-full sm:w-1/2 md:w-1/3 lg:w-1/4"
              />
            ))}
          </div>

          <Separator className="w-full max-w-2xl" />
          
          <div className="text-center space-y-2">
            <p className="text-sm text-muted-foreground">
              Built with modern web technologies
            </p>
            <p className="text-sm text-muted-foreground">
              © {currentYear} JIM. All rights reserved.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
