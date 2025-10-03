import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { AlertCircle, CheckCircle, Clock, Plus, Search, Filter } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';

interface MedicalCondition {
    id: number;
    condition_name: string;
    definition: string;
    classification?: string;
    incidence_rate?: number;
    prevalence_rate?: number;
    verified_by_nhs: boolean;
    professional_review_status: string;
    nhs_review_status: string;
    created_by: string;
    last_updated: string;
}

interface ProfessionalPrompt {
    id: number;
    title: string;
    prompt_text: string;
    prompt_category: string;
    clinical_context?: string;
    specialty?: string;
    difficulty_level: string;
    created_by_professional: string;
    professional_review_status: string;
    nhs_quality_check: boolean;
    usage_count: number;
    created_at: string;
}

const MedicalConditionManagement: React.FC = () => {
    const [conditions, setConditions] = useState<MedicalCondition[]>([]);
    const [prompts, setPrompts] = useState<ProfessionalPrompt[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('conditions');
    
    // Condition form state
    const [conditionForm, setConditionForm] = useState({
        condition_name: '',
        definition: '',
        classification: '',
        incidence_rate: '',
        prevalence_rate: '',
        aetiology: '',
        complications: '',
        primary_prevention: '',
        secondary_prevention: ''
    });
    
    // Prompt form state
    const [promptForm, setPromptForm] = useState({
        title: '',
        prompt_text: '',
        prompt_category: '',
        clinical_context: '',
        specialty: '',
        difficulty_level: 'intermediate'
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [conditionsRes, promptsRes] = await Promise.all([
                fetch('/api/medical-conditions/'),
                fetch('/api/professional-prompts/')
            ]);
            
            const conditionsData = await conditionsRes.json();
            const promptsData = await promptsRes.json();
            
            setConditions(conditionsData);
            setPrompts(promptsData);
            setLoading(false);
        } catch (error) {
            console.error('Error loading data:', error);
            setLoading(false);
        }
    };

    const handleConditionSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        try {
            const response = await fetch('/api/medical-conditions/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    ...conditionForm,
                    incidence_rate: conditionForm.incidence_rate ? parseFloat(conditionForm.incidence_rate) : null,
                    prevalence_rate: conditionForm.prevalence_rate ? parseFloat(conditionForm.prevalence_rate) : null
                })
            });
            
            if (response.ok) {
                await loadData();
                setConditionForm({
                    condition_name: '',
                    definition: '',
                    classification: '',
                    incidence_rate: '',
                    prevalence_rate: '',
                    aetiology: '',
                    complications: '',
                    primary_prevention: '',
                    secondary_prevention: ''
                });
            }
        } catch (error) {
            console.error('Error creating condition:', error);
        }
    };

    const handlePromptSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const clinicalCredentials = {
            professional_name: 'Dr. Admin Test',
            professional_title: 'Consultant Physician',
            specialty_expertise: 'General Medicine',
            years_experience: 15
        };
        
        try {
            const response = await fetch('/api/professional-prompts/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt_data: promptForm,
                    clinical_credentials: clinicalCredentials
                })
            });
            
            if (response.ok) {
                await loadData();
                setPromptForm({
                    title: '',
                    prompt_text: '',
                    prompt_category: '',
                    clinical_context: '',
                    specialty: '',
                    difficulty_level: 'intermediate'
                });
            }
        } catch (error) {
            console.error('Error creating prompt:', error);
        }
    };

    const getStatusBadge = (verified: boolean, reviewStatus: string) => {
        if (verified) {
            return <Badge variant="secondary" className="bg-green-100 text-green-800"><CheckCircle className="w-3 h-3 mr-1" />NHS Verified</Badge>;
        } else if (reviewStatus === 'pending') {
            return <Badge variant="secondary" className="bg-yellow-100 text-yellow-800"><Clock className="w-3 h-3 mr-1" />Pending Review</Badge>;
        } else {
            return <Badge variant="secondary" className="bg-red-100 text-red-800"><AlertCircle className="w-3 h-3 mr-1" />Needs Revision</Badge>;
        }
    };

    if (loading) {
        return <div className="p-6">Loading...</div>;
    }

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                    Medical Conditions & Professional Prompts Management
                </h1>
                <p className="text-gray-600">
                    Organize medical data and manage professional AI training prompts
                </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="conditions">Medical Conditions</TabsTrigger>
                    <TabsTrigger value="prompts">Professional Prompts</TabsTrigger>
                </TabsList>

                <TabsContent value="conditions">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Condition Form */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center">
                                    <Plus className="w-5 h-5 mr-2" />
                                    Add New Medical Condition
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleConditionSubmit} className="space-y-4">
                                    <div>
                                        <Label htmlFor="condition_name">Condition Name</Label>
                                        <Input
                                            id="condition_name"
                                            value={conditionForm.condition_name}
                                            onChange={(e) => setConditionForm({...conditionForm, condition_name: e.target.value})}
                                            required
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="definition">Definition</Label>
                                        <Textarea
                                            id="definition"
                                            value={conditionForm.definition}
                                            onChange={(e) => setConditionForm({...conditionForm, definition: e.target.value})}
                                            required
                                            rows={3}
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="classification">Classification</Label>
                                        <Input
                                            id="classification"
                                            value={conditionForm.classification}
                                            onChange={(e) => setConditionForm({...conditionForm, classification: e.target.value})}
                                        />
                                    </div>
                                    
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <Label htmlFor="incidence_rate">Incidence Rate (per 1000)</Label>
                                            <Input
                                                id="incidence_rate"
                                                type="number"
                                                step="0.1"
                                                value={conditionForm.incidence_rate}
                                                onChange={(e) => setConditionForm({...conditionForm, incidence_rate: e.target.value})}
                                            />
                                        </div>
                                        
                                        <div>
                                            <Label htmlFor="prevalence_rate">Prevalence Rate (per 1000)</Label>
                                            <Input
                                                id="prevalence_rate"
                                                type="number"
                                                step="0.1"
                                                value={conditionForm.prevalence_rate}
                                                onChange={(e) => setConditionForm({...conditionForm, prevalence_rate: e.target.value})}
                                            />
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="aetiology">Aetiology</Label>
                                        <Textarea
                                            id="aetiology"
                                            value={conditionForm.aetiology}
                                            onChange={(e) => setConditionForm({...conditionForm, aetiology: e.target.value})}
                                            rows={3}
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="complications">Complications</Label>
                                        <Textarea
                                            id="complications"
                                            value={conditionForm.complications}
                                            onChange={(e) => setConditionForm({...conditionForm, complications: e.target.value})}
                                            rows={2}
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="primary_prevention">Primary Prevention</Label>
                                        <Textarea
                                            id="primary_prevention"
                                            value={conditionForm.primary_prevention}
                                            onChange={(e) => setConditionForm({...conditionForm, primary_prevention: e.target.value})}
                                            rows={2}
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="secondary_prevention">Secondary Prevention</Label>
                                        <Textarea
                                            id="secondary_prevention"
                                            value={conditionForm.secondary_prevention}
                                            onChange={(e) => setConditionForm({...conditionForm, secondary_prevention: e.target.value})}
                                            rows={2}
                                        />
                                    </div>
                                    
                                    <Button type="submit" className="w-full">
                                        Add Medical Condition
                                    </Button>
                                </form>
                            </CardContent>
                        </Card>

                        {/* Conditions List */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Medical Conditions ({conditions.length})</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {conditions.map((condition) => (
                                        <div key={condition.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <h3 className="font-semibold text-lg">{condition.condition_name}</h3>
                                                {getStatusBadge(condition.verified_by_nhs, condition.nhs_review_status)}
                                            </div>
                                            
                                            <p className="text-sm text-gray-600 mb-2">
                                                {condition.definition.substring(0, 150)}...
                                            </p>
                                            
                                            <div className="flex justify-between text-xs text-gray-500">
                                                <span>By: {condition.created_by}</span>
                                                <span>
                                                    {condition.incidence_rate && `Incidence: ${condition.incidence_rate}/1000`}
                                                    {condition.prevalence_rate && ` Prevalence: ${condition.prevalence_rate}/1000`}
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                <TabsContent value="prompts">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Prompt Form */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center">
                                    <Plus className="w-5 h-5 mr-2" />
                                    Add Professional Prompt
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handlePromptSubmit} className="space-y-4">
                                    <div>
                                        <Label htmlFor="title">Prompt Title</Label>
                                        <Input
                                            id="title"
                                            value={promptForm.title}
                                            onChange={(e) => setPromptForm({...promptForm, title: e.target.value})}
                                            required
                                        />
                                    </div>
                                    
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <Label htmlFor="prompt_category">Category</Label>
                                            <Select
                                                value={promptForm.prompt_category}
                                                onValueChange={(value) => setPromptForm({...promptForm, prompt_category: value})}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select category" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="diagnosis">Diagnosis</SelectItem>
                                                    <SelectItem value="treatment">Treatment</SelectItem>
                                                    <SelectItem value="assessment">Assessment</SelectItem>
                                                    <SelectItem value="management">Management</SelectItem>
                                                    <SelectItem value="prevention">Prevention</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        
                                        <div>
                                            <Label htmlFor="specialty">Specialty</Label>
                                            <Input
                                                id="specialty"
                                                value={promptForm.specialty}
                                                onChange={(e) => setPromptForm({...promptForm, specialty: e.target.value})}
                                                placeholder="e.g., Cardiology, Neurology"
                                            />
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="clinical_context">Clinical Context</Label>
                                        <Textarea
                                            id="clinical_context"
                                            value={promptForm.clinical_context}
                                            onChange={(e) => setPromptForm({...promptForm, clinical_context: e.target.value})}
                                            rows={2}
                                            placeholder="When to use this prompt..."
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="prompt_text">Prompt Text</Label>
                                        <Textarea
                                            id="prompt_text"
                                            value={promptForm.prompt_text}
                                            onChange={(e) => setPromptForm({...promptForm, prompt_text: e.target.value})}
                                            required
                                            rows={4}
                                            placeholder="Enter the prompt that will train the AI model..."
                                        />
                                    </div>
                                    
                                    <div>
                                        <Label htmlFor="difficulty_level">Difficulty Level</Label>
                                        <Select
                                            value={promptForm.difficulty_level}
                                            onValueChange={(value) => setPromptForm({...promptForm, difficulty_level: value})}
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="basic">Basic</SelectItem>
                                                <SelectItem value="intermediate">Intermediate</SelectItem>
                                                <SelectItem value="advanced">Advanced</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    
                                    <Button type="submit" className="w-full">
                                        Submit Professional Prompt
                                    </Button>
                                </form>
                            </CardContent>
                        </Card>

                        {/* Prompts List */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Professional Prompts ({prompts.length})</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {prompts.map((prompt) => (
                                        <div key={prompt.id} className="border rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <h3 className="font-semibold text-lg">{prompt.title}</h3>
                                                <div className="flex gap-2">
                                                    {getStatusBadge(prompt.nhs_quality_check, prompt.professional_review_status)}
                                                    <Badge variant="outline">{prompt.prompt_category}</Badge>
                                                </div>
                                            </div>
                                            
                                            <p className="text-sm text-gray-600 mb-2">
                                                {prompt.prompt_text.substring(0, 150)}...
                                            </p>
                                            
                                            <div className="flex justify-between text-xs text-gray-500">
                                                <span>By: {prompt.created_by_professional}</span>
                                                <span>Used: {prompt.usage_count} times</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>

            <Alert className="mt-6">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                    <strong>Professional Training System:</strong> This system allows medical professionals to contribute prompts,
                    which are quality-checked by NHS professionals before being used to train the AI model. All submitted content 
                    follows the structured medical data organization format.
                </AlertDescription>
            </Alert>
        </div>
    );
};

export default MedicalConditionManagement;
