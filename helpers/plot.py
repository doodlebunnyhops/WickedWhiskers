

# Sample player data for testing the sweetness calculation
data = {
    'player_id': [1, 2, 3, 4, 5],
    'treats_given': [5, 2, 7, 3, 1],
    'total_candy_given': [50, 10, 70, 15, 5],
    'successful_tricks': [3, 1, 5, 0, 0],
    'failed_tricks': [1, 0, 2, 2, 0]
}

# Create a dictionary from the sample data
data_dict = {key: value for key, value in data.items()}

# Calculate sweetness using the new formula
# df['sweetness'] = (df['total_candy_given'] / df['treats_given']) - (2 * df['successful_tricks'] + df['failed_tricks'])
data_dict['sweetness'] = [(total_candy_given / treats_given) - (2 * successful_tricks + failed_tricks) for total_candy_given, treats_given, successful_tricks,failed_tricks in zip(data_dict['total_candy_given'], data_dict['treats_given'], data_dict['successful_tricks'], data_dict['failed_tricks'])]

# Print results by player_id
for player_id, sweetness in zip(data_dict['player_id'], data_dict['sweetness']):
    print(f"Player ID: {player_id}, Sweetness: {sweetness}")

# Sort players by sweetness
# df_sorted = df[['player_id', 'sweetness']].sort_values(by='sweetness', ascending=False)

# Display the sorted DataFrame
