import json
import re
import asyncio
import httpx
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

# Base URL for local downstream API requests
BASE_URL = getattr(settings, 'DISTRIBUTOR_BASE_URL', 'http://127.0.0.1:8000/api')

class DistributorAPIView(APIView):
    """
    API Gateway that accepts a large bulk JSON payload, sanitizes it,
    splits it into chunks, and asynchronously routes it to 12 downstream APIs.
    """
    
    def post(self, request, *args, **kwargs):
        # 1. Parse and sanitize the raw payload
        raw_body = request.body.decode('utf-8')
        
        # Simple cleanup for common JSON syntax errors mentioned in prompt 
        # (e.g., trailing commas before closing braces/brackets, semicolons instead of commas)
        cleaned_body = re.sub(r';\s*$', ',', raw_body, flags=re.MULTILINE)
        cleaned_body = re.sub(r'\"id\"\s*:\s*\d+\s*;', lambda m: m.group(0).replace(';', ','), cleaned_body)
        cleaned_body = re.sub(r',\s*([\]}])', r'\1', cleaned_body)
        
        try:
            payload = json.loads(cleaned_body)
        except json.JSONDecodeError as e:
            return Response(
                {"error": "Invalid JSON format in bulk payload.", "details": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Strip explicit 'id' keys recursively
        def strip_id_recursive(data):
            if isinstance(data, dict):
                data.pop('id', None)
                for v in data.values():
                    strip_id_recursive(v)
            elif isinstance(data, list):
                for item in data:
                    strip_id_recursive(item)
            return data
            
        payload = strip_id_recursive(payload)

        # 3. Dispatch requests asynchronously through phased pipeline
        results = asyncio.run(self._process_pipeline(payload))
        
        # 4. Summarize results
        failed_requests = {k: v for k, v in results.items() if v.get('status') not in [200, 201]}
        
        if failed_requests:
            return Response({
                "message": "Some bulk insertions failed.",
                "results": results
            }, status=status.HTTP_207_MULTI_STATUS)
            
        return Response({
            "message": "Bulk data successfully distributed to all downstream APIs.",
            "results": results
        }, status=status.HTTP_201_CREATED)


    async def _process_pipeline(self, payload):
        """Executes API HTTP POST requests in phases to inject auto-generated IDs."""
        results = {}
        async with httpx.AsyncClient() as client:
            
            async def send_post(key, url, json_payload):
                try:
                    resp = await client.post(url, json=json_payload)
                    try:
                        resp_json = resp.json()
                    except json.JSONDecodeError:
                        resp_json = resp.text
                    results[key] = {"status": resp.status_code, "response": resp_json}
                    return resp.status_code, resp_json
                except Exception as e:
                    results[key] = {"status": 500, "error": str(e)}
                    return 500, None

            # --- PHASE 1: Teams (to get auto-generated IDs) ---
            teams_data = payload.get("Teams", {})
            team_a_data = teams_data.get("Team_A", {})
            team_b_data = teams_data.get("Team_B", {})
            
            tasks_phase_1 = []
            if team_a_data:
                team_a_payload = {
                    "name": team_a_data.get("name"),
                    "coach": team_a_data.get("Coach"),
                    "manager": team_a_data.get("Manager"),
                    "supporting_staff": team_a_data.get("SupportingStaff")
                }
                tasks_phase_1.append(send_post('teams_a', f"{BASE_URL}/teams/", team_a_payload))
                
            if team_b_data:
                team_b_payload = {
                    "name": team_b_data.get("name"),
                    "coach": team_b_data.get("Coach"),
                    "manager": team_b_data.get("Manager"),
                    "supporting_staff": team_b_data.get("SupportingStaff")
                }
                tasks_phase_1.append(send_post('teams_b', f"{BASE_URL}/teams/", team_b_payload))
                
            if tasks_phase_1:
                await asyncio.gather(*tasks_phase_1)
                
            # Extract auto-generated IDs from Phase 1
            team_a_id = results.get('teams_a', {}).get('response', {}).get('id') if isinstance(results.get('teams_a', {}).get('response'), dict) else None
            team_b_id = results.get('teams_b', {}).get('response', {}).get('id') if isinstance(results.get('teams_b', {}).get('response'), dict) else None

            # --- PHASE 2: Match Details ---
            tasks_phase_2 = []

            # Match Details
            if "match_details" in payload:
                md_payload = payload["match_details"].copy()
                if team_a_id is not None:
                    md_payload["team_A_id"] = team_a_id
                if team_b_id is not None:
                    md_payload["teamB_id"] = team_b_id
                tasks_phase_2.append(send_post('match-details', f"{BASE_URL}/match-details/", md_payload))

            if tasks_phase_2:
                await asyncio.gather(*tasks_phase_2)
                
            # Extract auto-generated match ID from Phase 2
            match_id = results.get('match-details', {}).get('response', {}).get('id') if isinstance(results.get('match-details', {}).get('response'), dict) else None

            # --- PHASE 3: Players and all other endpoints ---
            tasks_phase_3 = []
            
            def inject_match_id(target_payload):
                if match_id is not None:
                    target_payload['match_id'] = match_id
                return target_payload

            # Players (Does not require matchId, only team ID)
            if team_a_data.get("Players") and team_a_id is not None:
                for idx, player_name in enumerate(team_a_data["Players"]):
                    p_payload = {"name": player_name, "team": team_a_id, "chest_number": idx + 1}
                    tasks_phase_3.append(send_post(f'player_{player_name}', f"{BASE_URL}/players/", p_payload))
            
            if team_b_data.get("Players") and team_b_id is not None:
                for idx, player_name in enumerate(team_b_data["Players"]):
                    p_payload = {"name": player_name, "team": team_b_id, "chest_number": idx + 1}
                    tasks_phase_3.append(send_post(f'player_{player_name}', f"{BASE_URL}/players/", p_payload))

            # Tournaments
            if "Tournament" in payload:
                t_payload = {"name": payload.get("Tournament"), "venue": payload.get("Venue", "")}
                tasks_phase_3.append(send_post('tournaments', f"{BASE_URL}/tournaments/", inject_match_id(t_payload)))
                
            # Defence
            if "defence" in payload:
                tasks_phase_3.append(send_post('defence', f"{BASE_URL}/defence/", inject_match_id({"Team_A": payload["defence"].get("Team_A", {}), "Team_B": payload["defence"].get("Team_B", {})})))

            # Chase
            if "chase" in payload:
                tasks_phase_3.append(send_post('chase', f"{BASE_URL}/chase/", inject_match_id({"Team_A": payload["chase"].get("Team_A", {}), "Team_B": payload["chase"].get("Team_B", {})})))

            # Substitutions
            if "Substitutions" in payload:
                formatted_subs = {"TeamA": [], "TeamB": []}
                for sub in payload["Substitutions"].get("Team_A", []):
                    if len(sub) == 2:
                        formatted_subs["TeamA"].append({"player_in": sub[0], "player_out": sub[1]})
                for sub in payload["Substitutions"].get("Team_B", []):
                    if len(sub) == 2:
                        formatted_subs["TeamB"].append({"player_in": sub[0], "player_out": sub[1]})
                tasks_phase_3.append(send_post('substitutions', f"{BASE_URL}/substitutions/", inject_match_id({"Substitutions": formatted_subs})))

            # Extra Points
            if "Extra_Points" in payload:
                tasks_phase_3.append(send_post('extra_points', f"{BASE_URL}/extra_points/", inject_match_id({"Team_A": payload["Extra_Points"].get("Team_A", {}), "Team_B": payload["Extra_Points"].get("Team_B", {})})))

            # Running Batch
            if "running_batch" in payload:
                tasks_phase_3.append(send_post('running_batch', f"{BASE_URL}/running_batch/", inject_match_id({"Team_A": payload["running_batch"].get("Team_A", {}), "Team_B": payload["running_batch"].get("Team_B", {})})))

            # Score Card
            if "score_card" in payload:
                tasks_phase_3.append(send_post('score_card', f"{BASE_URL}/score_card/", inject_match_id({"Team_A": payload["score_card"].get("Team_A", {}), "Team_B": payload["score_card"].get("Team_B", {})})))

            # Result
            if "result" in payload:
                res_data = payload["result"]
                formatted_result = {
                    "team_a_total": res_data.get("team_a_total"),
                    "team_b_total": res_data.get("team_b_total"),
                    "won_by": res_data.get("won_by"),
                    "team_won": res_data.get("team_won"),
                    "team_A": {
                        "I": res_data.get("team_A", {}).get("I", []),
                        "II": res_data.get("team_A", {}).get("II", []),
                        "III": res_data.get("team_A", {}).get("III", []),
                        "IV": res_data.get("team_A", {}).get("IV", "")
                    },
                    "team_B": {
                        "I": res_data.get("team_B", {}).get("I", []),
                        "II": res_data.get("team_B", {}).get("II", []),
                        "III": res_data.get("team_B", {}).get("III", []),
                        "IV": res_data.get("team_B", {}).get("IV", "")
                    }
                }
                tasks_phase_3.append(send_post('result', f"{BASE_URL}/result/", inject_match_id(formatted_result)))

            # Match Staff
            if "match_staff" in payload:
                ms_payload = payload["match_staff"].copy()
                tasks_phase_3.append(send_post('match-staff', f"{BASE_URL}/match-staff/", inject_match_id(ms_payload)))

            if tasks_phase_3:
                await asyncio.gather(*tasks_phase_3)
                
            return results
