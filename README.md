# Village Data App

## Access

Request user access from me, then use the below link.

**[https://village.streamlit.app](https://village.streamlit.app)**

It's hosted on Streamlit Community Cloud.

## Description

Village Data is a Streamlit-based web application that provides insights into rental property data. It offers features such as price tracking, live data fetching, and historical data analysis for various properties and units.

## Features

1. **Price Tracker**:

   - View rent summaries for selected properties
   - Analyze price changes over time
   - Visualize rent history for multiple units
   - Explore specific unit price history

2. **Live Data**:

   - Fetch and display current rental rates
   - View detailed unit information including amenities and floorplans

3. **Authentication**:
   - Secure login using AWS Cognito
   - Session management with AWS credentials

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/village-data-app.git
   cd village-data-app
   ```

2. Install required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add the following variables:
   ```env
   API_URL=<your_api_url>
   BUCKET=<your_s3_bucket_name>
   PREFIX=<your_s3_prefix>
   AWS_REGION=<your_aws_region>
   COGNITO_DOMAIN=<your_cognito_domain>
   CLIENT_ID=<your_client_id>
   CLIENT_SECRET=<your_client_secret>
   APP_URI=<your_app_uri>
   COGNITO_USER_POOL_ID=<your_user_pool_id>
   COGNITO_IDENTITY_POOL_ID=<your_identity_pool_id>
   ```

## Usage

Run the Streamlit app:

```bash
streamlit run app.py
```

Navigate to the provided URL in your web browser. Log in using your credentials to access the application features.

## Dependencies

- streamlit
- pandas
- plotly
- awswrangler
- boto3
- requests
- pytz

## Upcoming Features

- Price drop notifications
- Advanced filtering options
- New units added section
- Price changes by number of bedrooms

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [MIT License](LICENSE).
