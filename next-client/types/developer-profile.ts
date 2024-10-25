export interface DeveloperProfile {
    name: string
    role: string
    githubUsername: string
    linkedinUsername: string
    avatarUrl: string
}

export interface DeveloperCardProps extends DeveloperProfile {
    className?: string
}