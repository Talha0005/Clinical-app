import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface ChatMessageProps {
  message: string;
  sender: "doctor" | "user";
  timestamp?: string;
}

export const ChatMessage = ({ message, sender, timestamp }: ChatMessageProps) => {
  const isDoctor = sender === "doctor";
  
  return (
    <div className={`flex gap-3 ${isDoctor ? "" : "flex-row-reverse"} max-w-4xl mx-auto px-4 mb-6`}>
      {isDoctor && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarImage src="/api/placeholder/32/32" alt="Dr. Hervix" />
          <AvatarFallback className="bg-medical-blue text-white text-sm">
            DH
          </AvatarFallback>
        </Avatar>
      )}
      
      <div className={`flex flex-col ${isDoctor ? "items-start" : "items-end"} max-w-[85%]`}>
        <div
          className={`px-4 py-3 rounded-2xl ${
            isDoctor
              ? "bg-chat-bubble-doctor text-medical-text rounded-tl-md"
              : "bg-chat-bubble-user text-white rounded-tr-md"
          }`}
        >
          <p className="text-sm leading-relaxed">{message}</p>
        </div>
        
        {timestamp && (
          <span className="text-xs text-medical-text-muted mt-1 px-1">
            {timestamp}
          </span>
        )}
      </div>
    </div>
  );
};