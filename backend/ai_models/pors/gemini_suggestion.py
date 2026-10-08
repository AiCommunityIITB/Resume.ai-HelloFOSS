import os
import json
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import google.generativeai as genai
from typing import Dict, List, Union, Optional
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def safe_parse_por(por_data: Union[str, Dict]) -> Dict:
    """
    Safely parse POR data whether it's a string or dictionary.
    
    Args:
        por_data: POR data that could be a JSON string or dictionary
        
    Returns:
        Dictionary representation of the POR
    """
    if isinstance(por_data, str):
        try:
            return json.loads(por_data)
        except json.JSONDecodeError:
            return {}
    elif isinstance(por_data, dict):
        return por_data
    else:
        return {}

def safe_get_list(data: Dict, key: str, default: Optional[List] = None) -> List:
    """
    Safely get a list value from dictionary, handling various data types.
    
    Args:
        data: Dictionary to get value from
        key: Key to look for
        default: Default value if key not found
        
    Returns:
        List value
    """
    if default is None:
        default = []
        
    value = data.get(key, default)
    
    if isinstance(value, str):
        if value.strip():
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else [value]
            except json.JSONDecodeError:
                return [value]
        else:
            return []
    elif isinstance(value, list):
        return value
    elif value is None:
        return []
    else:
        return [str(value)]

def generate_enhanced_por_prompt(user_por: Union[str, Dict], similar_pors: List[Union[str, Dict]]) -> str:
    """
    Generates an enhanced, structured prompt for Gemini to get actionable POR improvement suggestions.
    
    Args:
        user_por: A dictionary or JSON string representing the user's POR.
        similar_pors: A list of dictionaries or JSON strings of similar high-quality PORs.
    
    Returns:
        A string containing the optimized prompt for the Gemini API.
    """
    user_por_dict = safe_parse_por(user_por)
    
    prompt = """You are an expert resume consultant specializing in optimizing "Position of Responsibility" (POR) entries for maximum impact. Your task is to transform the user's POR into a compelling, results-driven narrative that showcases leadership, quantifiable achievements, and professional growth.

## USER'S CURRENT POR:
"""
    
    # Format user POR with better structure
    prompt += f"**Title:** {user_por_dict.get('title', 'N/A')}\n"
    prompt += f"**Organization:** {user_por_dict.get('organization', 'N/A')}\n"
    prompt += f"**Duration:** {user_por_dict.get('duration', 'N/A')}\n"
    
    responsibilities = safe_get_list(user_por_dict, 'responsibilities')
    achievements = safe_get_list(user_por_dict, 'achievements')
    
    if responsibilities:
        prompt += f"**Current Responsibilities:**\n"
        for i, resp in enumerate(responsibilities, 1):
            prompt += f"  {i}. {resp}\n"
    
    if achievements:
        prompt += f"**Current Achievements:**\n"
        for i, ach in enumerate(achievements, 1):
            prompt += f"  {i}. {ach}\n"
    
    prompt += "\n## REFERENCE PORs (BEST PRACTICES):\n"
    prompt += "Use these high-quality examples to understand effective formatting and content strategies:\n\n"
    
    for i, por in enumerate(similar_pors, 1):
        por_dict = safe_parse_por(por)
        
        prompt += f"### Example {i}:\n"
        prompt += f"**Title:** {por_dict.get('title', 'N/A')}\n"
        prompt += f"**Organization:** {por_dict.get('organisation', por_dict.get('organization', 'N/A'))}\n"
        
        similar_responsibilities = safe_get_list(por_dict, 'responsibilities')
        similar_achievements = safe_get_list(por_dict, 'achievements')
        
        if similar_responsibilities or similar_achievements:
            prompt += f"**Key Points:**\n"
            all_points = similar_responsibilities + similar_achievements
            for point in all_points[:4]:  # Limit to top 4 points for brevity
                prompt += f"  • {point}\n"
        
        prompt += "\n"
    
    prompt += """
## ENHANCEMENT GUIDELINES:

### 1. **Action Verb Optimization**
   - Replace weak verbs (managed, handled, worked on) with powerful action words
   - Use: Led, Spearheaded, Orchestrated, Transformed, Achieved, Delivered, Optimized

### 2. **Quantification Strategy**
   - Add specific metrics: percentages, numbers, timeframes, scope
   - Include: team size, budget managed, people impacted, growth achieved
   - Example: "Increased engagement by 40%" vs "Improved engagement"

### 3. **Impact & Results Focus**
   - Lead with outcomes, not just activities
   - Show value creation and problem-solving
   - Demonstrate leadership influence and strategic thinking

### 4. **Professional Language**
   - Use industry-standard terminology
   - Maintain concise, impactful phrasing
   - Ensure each bullet point tells a complete story

### 5. **Structure & Flow**
   - Start bullets with strong action verbs
   - Follow: Action → Method → Result format
   - Maintain parallel structure across bullets

## OUTPUT REQUIREMENTS:

You must return a valid JSON response with exactly this structure:

{
"enhanced_por": {
"title": "Complete title with organization and duration (e.g., 'President, Student Council, XYZ University (Jan 2024 – Dec 2024)')",
"bullet_points": [
"Maximum 4 enhanced bullet points that showcase leadership, quantifiable achievements, and strategic impact",
"Each bullet should be 15-25 words and follow Action → Method → Result format",
"Include specific metrics, numbers, and measurable outcomes where possible",
"Use powerful action verbs and professional language throughout"
],
"key_improvements": [
"Specific explanation of what was enhanced (e.g., 'Added quantifiable metrics showing 40% improvement')",
"Reasoning for language changes (e.g., 'Replaced 'helped' with 'spearheaded' to show leadership')",
"Impact of structural improvements (e.g., 'Reorganized bullets to lead with outcomes first')",
"Professional terminology upgrades made"
]
},
"enhancement_summary": {
"primary_focus": "Main area of improvement (e.g., 'Quantification and Impact Measurement')",
"strength_areas": ["List of 2-3 key strengths highlighted in the enhancement"],
"impact_score": "Numeric rating (1-10) indicating the improvement level achieved"
}
}

Focus on creating a compelling narrative that positions the candidate as a results-driven leader with measurable impact."""
    
    return prompt

def get_enhanced_gemini_suggestions_sync(prompt: str) -> Dict:
    """
    Synchronous version of Gemini API call for use in thread pools.
    
    Args:
        prompt: The structured prompt to send to Gemini.
    
    Returns:
        Dictionary containing the parsed JSON response from Gemini API.
    """
    try:
        # Configure API key
        api_key = API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Gemini API key not configured. Please set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=api_key)
        
        # Initialize the model with Pro version for better reasoning
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Enhanced generation configuration
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Lower temperature for more consistent, professional output
            top_p=0.8,
            top_k=40,
            response_mime_type="application/json",  # Ensure JSON response
        )
        
        # Generate content with enhanced configuration
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if not response.text:
            return {
                "error": "No response generated from Gemini API",
                "enhanced_por": None,
                "enhancement_summary": None
            }
        
        try:
            # Parse the JSON response
            parsed_response = json.loads(response.text)
            return parsed_response
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse JSON response: {str(e)}",
                "raw_response": response.text,
                "enhanced_por": None,
                "enhancement_summary": None
            }
        
    except Exception as e:
        return {
            "error": f"Error generating suggestions: {str(e)}",
            "enhanced_por": None,
            "enhancement_summary": None
        }

async def get_enhanced_gemini_suggestions(prompt: str) -> Dict:
    """
    Asynchronous wrapper for Gemini API call using thread pool executor.
    
    Args:
        prompt: The structured prompt to send to Gemini.
    
    Returns:
        Dictionary containing the parsed JSON response from Gemini API.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(
            executor, 
            get_enhanced_gemini_suggestions_sync, 
            prompt
        )
    return result

async def process_single_por_concurrent(semaphore: asyncio.Semaphore, por_data: Dict, por_index: int) -> Dict:
    """
    Process a single POR with concurrency control using semaphore.
    
    Args:
        semaphore: Asyncio semaphore for controlling concurrency
        por_data: Dictionary containing POR data and similar PORs
        por_index: Index of the POR being processed
    
    Returns:
        Dictionary with processing results and metadata
    """
    async with semaphore:
        start_time = time.time()
        
        print(f"Starting processing POR {por_index + 1}...")
        
        user_por = por_data.get('user_por', {})
        similar_pors = por_data.get('similar_pors', [])
        
        # Initialize result structure
        result = {
            'por_index': por_index,
            'user_por': user_por,
            'similar_pors': similar_pors,
            'processing_status': 'success',
            'enhanced_suggestions': None,
            'error': None,
            'processing_time': 0
        }
        
        # Skip if there's already an error
        if por_data.get('error'):
            result['processing_status'] = 'skipped'
            result['error'] = por_data.get('error')
            result['processing_time'] = time.time() - start_time
            print(f"Skipped POR {por_index + 1}: {por_data.get('error')}")
            return result
        
        # Validate input data
        if not user_por:
            result['processing_status'] = 'failed'
            result['error'] = 'No user POR data provided'
            result['processing_time'] = time.time() - start_time
            print(f"Failed POR {por_index + 1}: No user POR data")
            return result
        
        try:
            # Generate enhanced prompt and get suggestions
            prompt = generate_enhanced_por_prompt(user_por, similar_pors)
            suggestions = await get_enhanced_gemini_suggestions(prompt)
            
            # Check if suggestions contain an error
            if suggestions.get('error'):
                result['processing_status'] = 'failed'
                result['error'] = suggestions['error']
                if 'raw_response' in suggestions:
                    result['raw_response'] = suggestions['raw_response']
                print(f"API Error for POR {por_index + 1}: {suggestions['error']}")
            else:
                result['enhanced_suggestions'] = suggestions
                print(f"Successfully processed POR {por_index + 1}")
            
        except Exception as e:
            result['processing_status'] = 'failed'
            result['error'] = f"Unexpected error: {str(e)}"
            print(f"Exception for POR {por_index + 1}: {str(e)}")
        
        finally:
            result['processing_time'] = time.time() - start_time
            print(f"Completed POR {por_index + 1} in {result['processing_time']:.2f}s")
        
        return result

async def concurrent_generate_enhanced_por_suggestions(all_por_data: List[Dict], max_concurrency: int = 4) -> List[Dict]:
    """
    Generate enhanced suggestions for multiple PORs concurrently with controlled concurrency.
    
    Args:
        all_por_data: List of dictionaries containing user_por and similar_pors for each POR
        max_concurrency: Maximum number of concurrent API calls (default: 5)
    
    Returns:
        List of dictionaries with enhanced suggestions and metadata for each POR
    """
    print(f"Starting concurrent processing of {len(all_por_data)} PORs with max_concurrency={max_concurrency}...")
    
    # Create semaphore to control concurrency
    semaphore = asyncio.Semaphore(max_concurrency)
    
    # Create tasks for all PORs
    tasks = []
    for i, por_data in enumerate(all_por_data):
        task = asyncio.create_task(
            process_single_por_concurrent(semaphore, por_data, i)
        )
        tasks.append(task)
    
    # Execute all tasks concurrently and wait for completion
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Handle any exceptions that occurred during processing
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                'por_index': i,
                'user_por': all_por_data[i].get('user_por', {}),
                'similar_pors': all_por_data[i].get('similar_pors', []),
                'processing_status': 'failed',
                'enhanced_suggestions': None,
                'error': f"Task exception: {str(result)}",
                'processing_time': 0
            })
        else:
            processed_results.append(result)
    
    # Print comprehensive summary
    successful = sum(1 for r in processed_results if r['processing_status'] == 'success')
    failed = sum(1 for r in processed_results if r['processing_status'] == 'failed')
    skipped = sum(1 for r in processed_results if r['processing_status'] == 'skipped')
    
    # Estimate time savings compared to sequential processing
    avg_processing_time = sum(r.get('processing_time', 0) for r in processed_results) / len(processed_results)
    estimated_sequential_time = avg_processing_time * len(all_por_data)
    time_saved = max(0, estimated_sequential_time - total_time)
    print(f"  💡 Estimated time saved: {time_saved:.2f}s ({time_saved/estimated_sequential_time*100:.1f}%)")
    
    return processed_results

def format_enhanced_por_output(suggestions_data: Dict) -> str:
    """
    Format the enhanced POR suggestions into a readable string format.
    
    Args:
        suggestions_data: Dictionary containing enhanced POR suggestions
        
    Returns:
        Formatted string representation of the suggestions
    """
    if suggestions_data.get('error'):
        return f"❌ Error: {suggestions_data['error']}"
    
    enhanced_por = suggestions_data.get('enhanced_por', {})
    enhancement_summary = suggestions_data.get('enhancement_summary', {})
    
    if not enhanced_por:
        return "❌ No enhanced POR data available"
    
    output = "🎯 **ENHANCED POR**\n"
    output += "=" * 50 + "\n\n"
    
    # Enhanced POR section
    output += f"**Title:** {enhanced_por.get('title', 'N/A')}\n\n"
    
    bullet_points = enhanced_por.get('bullet_points', [])
    if bullet_points:
        output += "**Enhanced Bullet Points:**\n"
        for i, bullet in enumerate(bullet_points, 1):
            output += f"  {i}. {bullet}\n"
        output += "\n"
    
    # Key improvements section
    improvements = enhanced_por.get('key_improvements', [])
    if improvements:
        output += "🔧 **Key Improvements Made:**\n"
        for i, improvement in enumerate(improvements, 1):
            output += f"  {i}. {improvement}\n"
        output += "\n"
    
    # Enhancement summary
    if enhancement_summary:
        output += " **Enhancement Summary:**\n"
        output += f"  • Primary Focus: {enhancement_summary.get('primary_focus', 'N/A')}\n"
        
        strength_areas = enhancement_summary.get('strength_areas', [])
        if strength_areas:
            output += f"  • Strength Areas: {', '.join(strength_areas)}\n"
        
        impact_score = enhancement_summary.get('impact_score', 'N/A')
        output += f"  • Impact Score: {impact_score}/10\n"
    
    return output

# Example usage and testing function
async def test_concurrent_pipeline():
    """
    Test function to demonstrate the concurrent pipeline capabilities.
    """
    sample_user_pors = [
        {
            "title": "Event Coordinator",
            "organization": "Tech Club",
            "duration": "Jan 2024 - Dec 2024",
            "responsibilities": ["Organized events", "Managed team", "Coordinated with sponsors"],
            "achievements": ["Successfully conducted 5 events", "Increased attendance"]
        },
        {
            "title": "Marketing Lead",
            "organization": "Student Council",
            "duration": "Feb 2024 - Nov 2024",
            "responsibilities": ["Led marketing campaigns", "Managed social media"],
            "achievements": ["Increased followers by 50%", "Boosted event attendance"]
        },
        {
            "title": "Project Manager",
            "organization": "Engineering Society",
            "duration": "Mar 2024 - Oct 2024",
            "responsibilities": ["Managed project timelines", "Coordinated team activities"],
            "achievements": ["Delivered 3 projects on time", "Improved team efficiency"]
        }
    ]
    
    sample_similar_pors = [
        {
            "title": "Event Manager",
            "organization": "Engineering Society",
            "responsibilities": ["Led planning and execution of 12+ technical workshops reaching 500+ students",
                              "Orchestrated cross-functional team of 15 volunteers to deliver seamless event experiences",
                              "Secured $10K+ in sponsorships through strategic partnership development"]
        }
    ]
    
    # Prepare test data
    test_data = []
    for i, por in enumerate(sample_user_pors):
        test_data.append({
            "por_index": i,
            "user_por": por,
            "similar_pors": sample_similar_pors,
            "error": None
        })
    
    # Test concurrent processing
    print("Testing concurrent enhanced POR pipeline...")
    results = await concurrent_generate_enhanced_por_suggestions(test_data, max_concurrency=3)
    
    # Display results
    for result in results:
        print(f"\n--- POR {result['por_index'] + 1} ---")
        if result.get('enhanced_suggestions') and not result['enhanced_suggestions'].get('error'):
            formatted_output = format_enhanced_por_output(result['enhanced_suggestions'])
            print(formatted_output)
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
