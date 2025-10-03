import { Shield, Clock, LogOut, User, Settings } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { Link } from "react-router-dom";

export const MedicalHeader = () => {
  const { username, logout } = useAuth();

  return (
    <div className="bg-medical-surface border-b border-border px-4 py-3">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="flex items-center gap-3">
          <Avatar className="h-10 w-10">
            <AvatarImage src="/api/placeholder/40/40" alt="Dr. Hervix" />
            <AvatarFallback className="bg-medical-blue text-white font-semibold">
              DH
            </AvatarFallback>
          </Avatar>
          
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h1 className="font-semibold text-medical-text">Dr. Hervix</h1>
              <Badge className="bg-medical-green text-white text-xs px-2 py-0.5 h-5">
                Online
              </Badge>
            </div>
            <p className="text-sm text-medical-text-muted">GP & Medical Consultant</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 text-sm text-medical-text-muted">
            <Shield className="h-4 w-4" />
            <span>Secure</span>
          </div>
          
          <div className="flex items-center gap-1 text-sm text-medical-text-muted">
            <Clock className="h-4 w-4" />
            <span>Available 24/7</span>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-sm text-medical-text-muted">
              <User className="h-4 w-4" />
              <span>{username}</span>
            </div>
            
            <Link to="/prompts">
              <Button
                variant="ghost"
                size="sm"
                className="text-medical-text-muted hover:text-medical-text"
              >
                <Settings className="h-4 w-4" />
              </Button>
            </Link>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="text-medical-text-muted hover:text-medical-text"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};