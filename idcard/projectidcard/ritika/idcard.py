import streamlit as st

# Access the secret
secrets = st.secrets["CEERIINTERN_CREDENTIALS"]

# Print the secret values
print(secrets["type"])  # Should print "service_account"
print(secrets["project_id"])  # Should print "ceeriintern"
print(secrets["private_key_id"])  # Should print "440751c7bf053828b027d497e5aa1c31bb4e9157"
print(secrets["private_key"])  # Should print the private key contents
