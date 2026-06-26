import json
import unicodedata
import difflib
import time
import os
from datetime import datetime
from typing import List, Dict, Any, Union

# Constants
# Adjust PROJECT_ROOT if the script is not run from the 'src' directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to PROJECT_ROOT
OUTPUT_DIR = os.path.join(PROJECT_ROOT, '..', 'output')
RAW_DIR = os.path.join(OUTPUT_DIR, 'raw')
PROCESSED_DIR = os.path.join(OUTPUT_DIR, 'processed')
LOGS_DIR = os.path.join(OUTPUT_DIR, 'logs')

SQUAD_FILE = os.path.join(RAW_DIR, 'squad.json')
TACTICAL_FILE = os.path.join(RAW_DIR, 'tactical.json')
PLAYERS_OUTPUT_FILE = os.path.join(PROCESSED_DIR, 'players.json')
MERGE_REPORT_FILE = os.path.join(LOGS_DIR, 'merge_report.json')

# Merge configuration
NAME_SIMILARITY_THRESHOLD = 0.90

# Validation constants
MIN_AGE = 15
MIN_SALARY = 0

# Metadata fields that should NOT go into the 'attributes' dictionary
METADATA_FIELDS = [
    "name", "age", "position", "primary_position",
    "secondary_positions", "ca", "pa", "contract_expiry",
    "salary", "personality", "determination", "average_rating",
]


class MergeEngine:
    """
    MergeEngine class is responsible for combining player data from various
    sources (e.g., squad, tactical) into a single, processed dataset.
    It handles name normalization, similarity matching, data validation,
    and generates a detailed merge report.
    The architecture is designed for easy extension to new data sources
    like physical.json, mental.json, etc., without fundamental changes
    to the merging logic.
    """

    def __init__(self):
        """
        Initializes the MergeEngine with paths and data structures for storing
        raw data, processed data, and merge report statistics.
        """
        self.squad_data: List[Dict[str, Any]] = []
        self.tactical_data: List[Dict[str, Any]] = []
        self.processed_players: List[Dict[str, Any]] = []

        # Counters for summary report
        self.squad_players_count = 0
        self.tactical_players_count = 0
        self.merged_players_count = 0  # Number of players successfully added to processed_players.json
        self.missing_attribute_matches_count = 0  # Total instances where an attribute source couldn't be matched
        self.duplicate_tactical_match_count = 0  # Count of tactical players matched by multiple squad players
        self.invalid_player_count = 0  # Count of players failing validation checks

        # Structure for the detailed merge report
        self.merge_report: Dict[str, Any] = {
            "created_at": "",
            "processed_players_details": [],  # Details about each player's merge status
            "duplicate_tactical_matches": [],  # Instances of tactical players being matched multiple times
            "missing_attribute_matches": [],  # Instances where an attribute source was not found for a player
            "invalid_players": [],  # Players that failed validation checks
            "warnings": [],  # General warnings or errors during the process
        }

        # Ensure output directories exist before any file operations
        os.makedirs(PROCESSED_DIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)

    def load_json(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Loads JSON data from a specified file path. Includes error handling
        for file not found and JSON decoding issues.

        Args:
            file_path: The absolute path to the JSON file.

        Returns:
            A list of dictionaries containing the loaded JSON data.
            Returns an empty list if the file is not found or an error occurs,
            logging the issue to the merge report warnings.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            error_message = f"Error: File not found at {file_path}. Skipping data load."
            self.merge_report["warnings"].append(error_message)
            print(error_message)
            return []
        except json.JSONDecodeError:
            error_message = f"Error: Could not decode JSON from {file_path}. Check file format."
            self.merge_report["warnings"].append(error_message)
            print(error_message)
            return []
        except Exception as e:
            error_message = f"An unexpected error occurred while loading {file_path}: {e}"
            self.merge_report["warnings"].append(error_message)
            print(error_message)
            return []

    def save_json(self, data: Union[List[Dict[str, Any]], Dict[str, Any]], file_path: str) -> None:
        """
        Saves data as JSON to a specified file path.
        This method is generic and can save both the list of processed players
        and the detailed merge report.

        Args:
            data: The data to save (either a list of player dictionaries or a report dictionary).
            file_path: The absolute path to the output JSON file.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Data successfully saved to {file_path}")
        except IOError as e:
            error_message = f"Error: Could not write to file {file_path}: {e}"
            self.merge_report["warnings"].append(error_message)
            print(error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred while saving {file_path}: {e}"
            self.merge_report["warnings"].append(error_message)
            print(error_message)

    def normalize_name(self, name: str) -> str:
        """
        Normalizes a player's name by removing accents (diacritics),
        converting to lowercase, and stripping extra spaces.
        This helps in achieving consistent matching for names like
        "Jeremy Doku" and "Jérémy Doku".

        Args:
            name: The player's name as a string.

        Returns:
            The normalized name string.
        """
        # Remove accents/diacritics
        normalized_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
        # Convert to lowercase
        normalized_name = normalized_name.lower()
        # Replace multiple spaces with a single space and strip leading/trailing spaces
        normalized_name = ' '.join(normalized_name.split())
        return normalized_name

    def similarity(self, name1: str, name2: str) -> float:
        """
        Calculates the similarity ratio between two player names using
        difflib.SequenceMatcher. This allows for fuzzy matching of names.

        Args:
            name1: The first player's name (preferably normalized).
            name2: The second player's name (preferably normalized).

        Returns:
            A float representing the similarity ratio (0.0 to 1.0).
        """
        return difflib.SequenceMatcher(None, name1, name2).ratio()

    def index_players(self, players_list: List[Dict[str, Any]], source_name: str = "unknown") -> Dict[str, Dict[str, Any]]:
        """
        Creates an index of players using their normalized names as keys for
        efficient lookup. It handles cases where players might not have a name
        or have duplicate normalized names within the same source, logging warnings.

        Args:
            players_list: A list of player dictionaries from a specific source.
            source_name: The name of the data source (e.g., "squad", "tactical")
                         for more descriptive warning messages.

        Returns:
            A dictionary where keys are normalized player names and values are
            the corresponding player dictionaries. If duplicate normalized names
            are found, the first encountered player is kept in the index.
        """
        indexed_players = {}
        for i, player in enumerate(players_list):
            name = player.get("name")
            if not name:
                warning_message = f"Player at index {i} in {source_name} data has no 'name' field and will be skipped for indexing."
                self.merge_report["warnings"].append(warning_message)
                continue

            normalized_name = self.normalize_name(name)
            if normalized_name in indexed_players:
                # Log duplicate within the source but proceed, keeping the first entry
                warning_message = f"Duplicate normalized name '{normalized_name}' for player '{name}' found in {source_name} data. Keeping the first instance in the index."
                self.merge_report["warnings"].append(warning_message)
            else:
                indexed_players[normalized_name] = player
        return indexed_players

    def find_best_match(
        self,
        base_player: Dict[str, Any],
        target_indexed_players: Dict[str, Dict[str, Any]]
    ) -> Union[Dict[str, Any], None]:
        """
        Finds the best matching player from a target indexed list for a given
        base player based on name similarity. A match is only considered valid
        if its similarity ratio meets or exceeds `NAME_SIMILARITY_THRESHOLD`.

        Args:
            base_player: A dictionary representing a player from the primary data source.
            target_indexed_players: A dictionary of players from a secondary source,
                                    indexed by their normalized names.

        Returns:
            The dictionary of the best matching player from the target source,
            or None if no match above the threshold is found.
        """
        base_player_name = base_player.get("name")
        if not base_player_name:
            return None  # Cannot match a player without a name

        normalized_base_name = self.normalize_name(base_player_name)

        best_match: Union[Dict[str, Any], None] = None
        highest_similarity = 0.0

        for normalized_target_name, target_player in target_indexed_players.items():
            current_similarity = self.similarity(normalized_base_name, normalized_target_name)
            if current_similarity > highest_similarity:
                highest_similarity = current_similarity
                best_match = target_player

        if highest_similarity >= NAME_SIMILARITY_THRESHOLD and best_match:
            return best_match
        return None

    def extract_attributes(self, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts only the Football Manager attributes from a player's data,
        excluding common metadata fields defined in `METADATA_FIELDS`.

        Args:
            player_data: A dictionary containing a player's data (e.g., from tactical.json).

        Returns:
            A dictionary containing only the FM24 attributes.
        """
        attributes = {}
        for key, value in player_data.items():
            if key not in METADATA_FIELDS:
                attributes[key] = value
        return attributes

    def validate_player(self, player: Dict[str, Any]) -> bool:
        """
        Validates a player's data against defined business rules:
        - CA (Current Ability) must be less than or equal to PA (Potential Ability).
        - Age must be 15 or greater.
        - Salary must be 0 or greater.
        Logs any validation failures as warnings in the merge report and increments
        the `invalid_player_count`.

        Args:
            player: The player dictionary to validate.

        Returns:
            True if the player passes all validation checks, False otherwise.
        """
        is_valid = True
        player_name = player.get("name", "Unknown Player")
        current_player_validation_warnings = []

        # Validate CA <= PA
        ca = player.get("ca")
        pa = player.get("pa")
        if ca is not None and pa is not None:
            if not isinstance(ca, (int, float)) or not isinstance(pa, (int, float)):
                current_player_validation_warnings.append(f"{player_name}: CA or PA is not a valid number. (CA: {ca}, PA: {pa})")
                is_valid = False
            elif ca > pa:
                current_player_validation_warnings.append(f"{player_name}: CA ({ca}) is greater than PA ({pa}).")
                is_valid = False
        else:
             current_player_validation_warnings.append(f"{player_name}: Missing CA or PA for validation.")
             is_valid = False

        # Validate Age >= MIN_AGE
        age = player.get("age")
        if age is not None:
            if not isinstance(age, (int, float)):
                current_player_validation_warnings.append(f"{player_name}: Age is not a valid number. (Age: {age})")
                is_valid = False
            elif age < MIN_AGE:
                current_player_validation_warnings.append(f"{player_name}: Age ({age}) is less than {MIN_AGE}.")
                is_valid = False
        else:
            current_player_validation_warnings.append(f"{player_name}: Missing Age for validation.")
            is_valid = False

        # Validate Salary >= MIN_SALARY
        salary = player.get("salary")
        if salary is not None:
            if not isinstance(salary, (int, float)):
                current_player_validation_warnings.append(f"{player_name}: Salary is not a valid number. (Salary: {salary})")
                is_valid = False
            elif salary < MIN_SALARY:
                current_player_validation_warnings.append(f"{player_name}: Salary ({salary}) is less than {MIN_SALARY}.")
                is_valid = False
        else:
            current_player_validation_warnings.append(f"{player_name}: Missing Salary for validation.")
            is_valid = False

        if not is_valid:
            self.merge_report["invalid_players"].append({"name": player_name, "reasons": current_player_validation_warnings})
            self.invalid_player_count += 1
            # Add specific validation failures to general warnings as well
            self.merge_report["warnings"].extend(current_player_validation_warnings)

        return is_valid

    def merge(self) -> None:
        """
        Orchestrates the main merging logic. It iterates through squad players,
        attempts to find matches in defined attribute sources (e.g., tactical data),
        extracts and combines attributes, validates the resulting player data,
        and populates various sections of the merge report.
        This method is designed to be extensible, allowing new attribute sources
        to be added by simply modifying the `attribute_sources_to_merge` dictionary.
        """
        self.squad_players_count = len(self.squad_data)
        self.tactical_players_count = len(self.tactical_data)

        # Define all attribute sources that need to be merged into the base player data.
        # To add new sources (e.g., physical, mental), simply add an entry here.
        attribute_sources_to_merge: Dict[str, List[Dict[str, Any]]] = {
            "tactical": self.tactical_data,
            # Example for future extension:
            # "physical": self.physical_data,
            # "mental": self.mental_data,
            # "goalkeeper": self.goalkeeper_data,
        }

        # Index all attribute sources for efficient lookup during the merge process
        indexed_attribute_sources: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for source_name, source_data in attribute_sources_to_merge.items():
            indexed_attribute_sources[source_name] = self.index_players(source_data, source_name)

        # Track tactical players that have been successfully matched to detect if any tactical player
        # is matched by multiple squad players. This is specifically for the "duplicate_tactical_matches" report.
        used_tactical_player_normalized_names: set[str] = set()

        for squad_player in self.squad_data:
            player_name = squad_player.get("name", "Unknown Player from Squad")
            merged_player = squad_player.copy()  # Start with squad data as the base
            merged_player["attributes"] = {}  # Initialize attributes dictionary for the merged player

            # Record merge status for the current player for the detailed report
            current_player_merge_status = {
                "squad_name": player_name,
                "matched_sources": [],
                "missing_sources": []
            }

            # Iterate through each defined attribute source to find matches and extract attributes
            for source_key, indexed_data in indexed_attribute_sources.items():
                best_match_from_source = self.find_best_match(squad_player, indexed_data)

                if best_match_from_source:
                    source_player_name = best_match_from_source.get("name", f"Unknown Player from {source_key}")
                    normalized_source_player_name = self.normalize_name(source_player_name)

                    # Special handling for 'tactical' source to detect when a tactical player
                    # is matched by more than one squad player.
                    if source_key == "tactical":
                        if normalized_source_player_name in used_tactical_player_normalized_names:
                            self.duplicate_tactical_match_count += 1
                            self.merge_report["duplicate_tactical_matches"].append(
                                {
                                    "squad_name": player_name,
                                    "matched_tactical_name": source_player_name,
                                    "reason": "Tactical player was matched by multiple squad players."
                                }
                            )
                            warning_message = f"Tactical player '{source_player_name}' was matched by multiple squad players, including '{player_name}'. This indicates a potential duplicate match or issue in source data."
                            self.merge_report["warnings"].append(warning_message)
                        else:
                            used_tactical_player_normalized_names.add(normalized_source_player_name)

                    attributes_from_source = self.extract_attributes(best_match_from_source)
                    # Merge (update) attributes from the current source into the player's attributes dictionary
                    merged_player["attributes"].update(attributes_from_source)
                    current_player_merge_status["matched_sources"].append(source_key)
                else:
                    # Log if an attribute source could not be matched for the current squad player
                    current_player_merge_status["missing_sources"].append(source_key)
                    self.missing_attribute_matches_count += 1
                    self.merge_report["missing_attribute_matches"].append(
                        {"squad_name": player_name, "missing_source": source_key}
                    )
                    warning_message = f"Squad player '{player_name}' could not be matched with data from '{source_key}'."
                    self.merge_report["warnings"].append(warning_message)

            # After attempting to merge from all attribute sources for the current squad player:
            self.merged_players_count += 1  # Increment count for each player processed into the final list

            # Validate the complete merged player data
            # This call updates self.invalid_player_count and adds to self.merge_report["invalid_players"]
            self.validate_player(merged_player)

            self.processed_players.append(merged_player)
            self.merge_report["processed_players_details"].append(current_player_merge_status)

    def generate_report(self, start_time: float, end_time: float) -> None:
        """
        Generates the final merge report, including a summary of statistics
        and detailed logs of processing events. The report is then saved
        to `output/logs/merge_report.json`.

        Args:
            start_time: The timestamp (in seconds since epoch) when the merge process started.
            end_time: The timestamp (in seconds since epoch) when the merge process ended.
        """
        self.merge_report["created_at"] = datetime.now().isoformat()
        self.merge_report["summary"] = {
            "total_squad_players": self.squad_players_count,
            "total_tactical_players": self.tactical_players_count,
            "total_processed_players": self.merged_players_count,
            "total_missing_attribute_matches": self.missing_attribute_matches_count,
            "total_duplicate_tactical_matches": self.duplicate_tactical_match_count,
            "total_invalid_players": self.invalid_player_count,
            "total_warnings": len(self.merge_report["warnings"]),
            "execution_time_seconds": round(end_time - start_time, 2),
        }
        self.save_json(self.merge_report, MERGE_REPORT_FILE)

    def print_summary(self, execution_time: float) -> None:
        """
        Prints a concise summary of the merge operation to the console,
        providing key statistics at a glance.

        Args:
            execution_time: The total time taken for the merge process in seconds.
        """
        print("=" * 36)
        print("FM24 Merge Engine V2".center(36))
        print("=" * 36)
        print(f"Squad Players: {self.squad_players_count}")
        print(f"Tactical Players: {self.tactical_players_count}")
        print(f"Merged Players: {self.merged_players_count}")
        print(f"Missing Attribute Matches: {self.missing_attribute_matches_count}")
        print(f"Duplicate Tactical Matches: {self.duplicate_tactical_match_count}")
        print(f"Invalid Players: {self.invalid_player_count}")
        print(f"Execution Time: {execution_time:.2f} seconds")
        print("=" * 36)

    def run(self) -> None:
        """
        Executes the entire merge process. This includes loading raw data,
        performing the merge logic, saving the processed player data,
        generating a detailed report, and printing a summary to the console.
        """
        start_time = time.time()
        print("Starting FM24 Merge Engine...")

        # Load raw data from specified JSON files
        print(f"Loading squad data from {SQUAD_FILE}...")
        self.squad_data = self.load_json(SQUAD_FILE)
        print(f"Loading tactical data from {TACTICAL_FILE}...")
        self.tactical_data = self.load_json(TACTICAL_FILE)

        # Basic checks to ensure essential data is available before proceeding
        if not self.squad_data:
            print("Squad data not loaded. Cannot proceed with merge. Please ensure squad.json exists and is valid.")
            self.merge_report["warnings"].append("Squad data not loaded. Merge process aborted.")
            # Generate report and summary even if aborted
            self.generate_report(start_time, time.time())
            self.print_summary(time.time() - start_time)
            return

        if not self.tactical_data:
            print("Tactical data not loaded. Proceeding with only squad data. Player attributes will be empty.")
            self.merge_report["warnings"].append("Tactical data not loaded. Player attributes will be empty for all players.")

        # Execute the core merge logic
        print("Merging player data...")
        self.merge()

        # Save the final processed player data
        print(f"Saving processed players to {PLAYERS_OUTPUT_FILE}...")
        self.save_json(self.processed_players, PLAYERS_OUTPUT_FILE)

        end_time = time.time()
        execution_time = end_time - start_time

        # Generate and save the comprehensive merge report
        print(f"Generating merge report to {MERGE_REPORT_FILE}...")
        self.generate_report(start_time, end_time)

        # Print the summary of the operation to the console
        self.print_summary(execution_time)


# This ensures the MergeEngine can be instantiated and run directly when the script is executed.
if __name__ == "__main__":
    engine = MergeEngine()
    engine.run()
