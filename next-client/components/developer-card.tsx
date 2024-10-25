import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Card, CardContent } from "@/components/ui/card"
import { Github, Linkedin } from "lucide-react"
import { FC } from "react"
import { DeveloperCardProps } from "@/types/developer-profile"

const DeveloperCard: FC<DeveloperCardProps> = ({
    name,
    role,
    githubUsername,
    linkedinUsername,
    avatarUrl,
    className,
}) => (
    <Card className={`bg-background/50 backdrop-blur supports-[backdrop-filter]:bg-background/50 ${className}`}>
        <CardContent className="flex flex-col items-center p-4">
            <TooltipProvider>
                <Tooltip>
                    <TooltipTrigger asChild>
                        <div className="relative group cursor-pointer">
                            <div
                                className="absolute -inset-0.5 bg-gradient-to-r from-primary to-primary/50 rounded-full opacity-30 group-hover:opacity-100 transition duration-500"
                                aria-hidden="true"
                            />
                            <Avatar className="h-16 w-16 relative group-hover:scale-105 transition duration-300">
                                <AvatarImage src={avatarUrl} alt={name} />
                                <AvatarFallback className="bg-secondary">
                                    {name.split(' ').map(n => n[0]).join('')}
                                </AvatarFallback>
                            </Avatar>
                        </div>
                    </TooltipTrigger>
                    <TooltipContent>
                        <div className="text-sm space-y-1">
                            <p className="font-semibold">{name}</p>
                            <p className="text-xs text-muted-foreground">{role}</p>
                        </div>
                    </TooltipContent>
                </Tooltip>
            </TooltipProvider>

            <div className="mt-4 flex items-center space-x-3">
                <a
                    href={`https://github.com/${githubUsername}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-primary transition-colors p-2 hover:bg-primary/10 rounded-full"
                    aria-label={`${name}'s GitHub profile`}
                >
                    <Github className="h-4 w-4" />
                </a>
                <a
                    href={`https://linkedin.com/in/${linkedinUsername}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-primary transition-colors p-2 hover:bg-primary/10 rounded-full"
                    aria-label={`${name}'s LinkedIn profile`}
                >
                    <Linkedin className="h-4 w-4" />
                </a>
            </div>
        </CardContent>
    </Card>
)


export default DeveloperCard;
