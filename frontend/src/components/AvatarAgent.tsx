import React, { useState, useEffect } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, History, AlertTriangle, FileText, CheckCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AgentProgress {
  id: string;
  name: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  icon: React.ReactNode;
  description: string;
}

interface AvatarAgentProps {
  isActive: boolean;
  currentAgent?: string;
  agentProgress?: AgentProgress[];
  avatarUrl?: string;
  isSpeaking?: boolean;
  className?: string;
}

const defaultAgents: AgentProgress[] = [
  {
    id: 'avatar',
    name: 'Avatar',
    status: 'pending',
    icon: <Brain className="h-4 w-4" />,
    description: 'Understanding your message'
  },
  {
    id: 'history',
    name: 'History Taking',
    status: 'pending',
    icon: <History className="h-4 w-4" />,
    description: 'Collecting medical history'
  },
  {
    id: 'triage',
    name: 'Symptom Triage',
    status: 'pending',
    icon: <AlertTriangle className="h-4 w-4" />,
    description: 'Assessing urgency'
  },
  {
    id: 'summarisation',
    name: 'Summarisation',
    status: 'pending',
    icon: <FileText className="h-4 w-4" />,
    description: 'Creating summary'
  }
];

export const AvatarAgent: React.FC<AvatarAgentProps> = ({
  isActive,
  currentAgent,
  agentProgress = defaultAgents,
  avatarUrl,
  isSpeaking = false,
  className
}) => {
  const [agents, setAgents] = useState<AgentProgress[]>(agentProgress);

  useEffect(() => {
    setAgents(agentProgress);
  }, [agentProgress]);

  const getStatusIcon = (status: AgentProgress['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'active':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default:
        return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />;
    }
  };

  const getStatusColor = (status: AgentProgress['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'active':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };

  return (
    <div className={cn("flex flex-col items-center space-y-4", className)}>
      {/* Main Avatar */}
      <div className="relative">
        <Avatar className={cn(
          "h-20 w-20 border-4 transition-all duration-300",
          isActive ? "border-blue-500 shadow-lg" : "border-gray-200",
          isSpeaking && "animate-pulse"
        )}>
          <AvatarImage 
            src={avatarUrl || "/api/placeholder/80/80"} 
            alt="Dr. Hervix" 
          />
          <AvatarFallback className="text-2xl font-bold bg-blue-100 text-blue-800">
            DH
          </AvatarFallback>
        </Avatar>
        
        {/* Speaking indicator */}
        {isSpeaking && (
          <div className="absolute -bottom-2 -right-2 h-6 w-6 bg-green-500 rounded-full flex items-center justify-center">
            <div className="h-2 w-2 bg-white rounded-full animate-pulse" />
          </div>
        )}
      </div>

      {/* Agent Name */}
      <div className="text-center">
        <h3 className="font-semibold text-lg text-gray-900">Dr. Hervix</h3>
        <p className="text-sm text-gray-600">AI Medical Assistant</p>
      </div>

      {/* Agent Progress Chain */}
      {isActive && (
        <Card className="w-full max-w-md">
          <CardContent className="p-4">
            <div className="space-y-3">
              <h4 className="font-medium text-sm text-gray-700 mb-3">Processing your request...</h4>
              
              {agents.map((agent, index) => (
                <div key={agent.id} className="flex items-center space-x-3">
                  {/* Status Icon */}
                  <div className="flex-shrink-0">
                    {getStatusIcon(agent.status)}
                  </div>
                  
                  {/* Agent Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-900">
                        {agent.name}
                      </span>
                      <Badge 
                        variant="outline" 
                        className={cn("text-xs", getStatusColor(agent.status))}
                      >
                        {agent.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {agent.description}
                    </p>
                  </div>
                  
                  {/* Agent Icon */}
                  <div className="flex-shrink-0 text-gray-400">
                    {agent.icon}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Agent Status */}
      {currentAgent && (
        <div className="text-center">
          <Badge variant="secondary" className="text-xs">
            Currently: {currentAgent}
          </Badge>
        </div>
      )}
    </div>
  );
};
