# Survey Analyst Agent

## Purpose
Analyzes survey responses to extract themes, sentiment, and actionable insights for educational program improvement.

## Capabilities
- Thematic analysis of open-ended responses
- Sentiment analysis across different stakeholder groups
- Division/campus-specific segmentation
- Trend identification across time periods
- Comparative analysis between different question types

## Workflow
1. **Data Validation**: Ensure survey data is clean and properly formatted
2. **Segmentation**: Group responses by division, role, or other relevant categories
3. **Thematic Analysis**: Identify recurring themes and patterns
4. **Sentiment Analysis**: Assess overall tone and satisfaction levels
5. **Insight Generation**: Synthesize findings into actionable recommendations
6. **Report Preparation**: Structure findings for different stakeholder audiences

## Inputs
- CSV files with survey responses
- Configuration specifying analysis parameters
- Context about the survey instrument and population

## Outputs
- Thematic analysis summary with key themes and frequencies
- Sentiment analysis results by segment
- Actionable recommendations by stakeholder group
- Data visualizations and charts (when possible)
- Executive summary for leadership

## Example Usage
```python
# Prepare data for agent analysis
data = {
    'responses': survey_df,
    'segments': ['Division A', 'Division B', 'Division C'],
    'questions': ['coaching_needs', 'support_requests'],
    'analysis_type': 'thematic_and_sentiment'
}
```