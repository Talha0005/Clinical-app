import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

export const MedicalDisclaimer = () => {
  return (
    <div className="w-full flex justify-center m-4">
      <Alert className="bg-medical-warning/10 border-medical-warning/30 max-w-4xl w-full">
        <div className="flex items-center justify-center gap-2 w-full">
          <AlertTriangle className="h-4 w-4 text-medical-warning flex-shrink-0" />
          <AlertDescription className="text-medical-text text-center">
            <strong>Medical Disclaimer:</strong> This AI consultation is for informational purposes only. 
            For emergencies, call 999. Always consult with a qualified healthcare professional for medical advice.
          </AlertDescription>
        </div>
      </Alert>
    </div>
  );
};