import json
import re

raw_body = """{
  "Tournament": "",
  "Venue": "",
  "match_details": {
        "id": 4,
        "tournamentId": null,
        "match_no": 12,
        "date": "2026-03-16",
        "time": "15:30:00",
        "court_no": 2,
        "type": "League",
        "session": "Morning",
        "section": "SENIOR",
        "category": "MEN",
        "group": "A",
        "toss_winner": "Shivaji Warriors",
        "choice": "Attack",
        "batches": {
            "team_a": [
                [7, 9, 3],
                [5, 6, 2],
                [1, 4, 8]
            ],
            "team_b": [
                [2, 4, 6],
                [8, 10, 1],
                [3, 5, 7]
            ]
        }
    },
	
	
	

  "Teams": {
	
    "Team_A": {
	"id":1;
      "name":"AJIO Team",
      "Players": [
        "Rohit Patil"
      ],
      "Coach": "Rajendra Kulkarni",
      "Manager": "Sanjay Patil",
      "SupportingStaff": "Physio: Dr. Mehta"
    },

    "Team_B": {
	  "id":2,
      "name":"AMAR Team",
      "Players": [
        "Arjun Deshmukh"
      ],
      "Coach": "Vijay Kulkarni",
      "Manager": "Pradeep Patil",
      "SupportingStaff": "Physio: Dr. Joshi"
    }
  },
		
	"defence":{
		
 		 "Team_A": {

   			 "I": [
    				  ["00:30","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
    				  ["00:45","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
    				  ["00:50","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
    				],

  			"II": [
   				   ["01:00","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
   				   ["00:35","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
  				],

   			"III": [
    				  ["00:55","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
    				  ["01:05","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
    				],

    			"IV":  ["00:40","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
   
  			},

		"Team_B": {
 			 "I": [
    				  ["00:30","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
    				  ["00:45","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
    				  ["00:50","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
    				],

  			"II": [
   				   ["01:00","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
   				   ["00:35","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
  				],

   			"III": [
    				  ["00:55","-","-","-","-","-","-","-","-","-","-","-","-","-","-"],
    				  ["01:05","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
    				],

    			"IV":  ["00:40","-","-","-","-","-","-","-","-","-","-","-","-","-","-"]
  			}

		},

	"chase":{

		"Team_A": {
   			 "I": [7, 9, 3, 5],
    			"II": [2, 4, 6, 8, 10],
    			"III": [1, 11, 12],
    			"IV": [3, 5, 7, 9]
  		},

		"Team_B": {
   			 "I": [7, 9, 3, 5],
    			"II": [2, 4, 6, 8, 10],
    			"III": [1, 11, 12],
    			"IV": [3, 5, 7, 9]
  		}
	},

	
				
			
	  "Substitutions": {
			"Team_A": [
			 [ 7,  3],
			 [ 7,  3],
			  [ 7,  3],
			  [ 7,  3],
			],

			"Team_B": [
			  [ 7,  3],
			 [ 7,  3],
			  [ 7,  3],
			  [ 7,  3],
			]
	  },

	
	   
 	 
	
	"Extra_Points":{
  		"Team_A": {
    			"late_entry": [2, 4],
    			"out_of_field": [9],
	    		"warning": [15],
	    		"dream_run": [8]
 		 },

		"Team_B": {
    			"late_entry": [2, 4],
    			"out_of_field": [9],
	    		"warning": [15],
    			"dream_run": [8]
	 	 }
	},




	
  "running_batch":{
  	"Team_A": {
	    "turn_I": [	        
			 [7, 9, 3],
			 [5, 6],
	          	 [2]
		        ],
	      
	      
	        "turn_II":[
				[2, 4],
        			[8, 10, 1],
	   			[3],
	          		[6]
			],
	      
	      
	        "turn_III": [
        	  		[6, 7],
				[9],
				[11, 12],
        			[4]
	       		 ],
	      
	      
	        "turn_IV":[
			        [3],
	         		[5, 8]
	       		 ]
	      
		  },
	
	"Team_B": {
	    "turn_I": [	        
			 [7, 9, 3],
			 [5, 6],
	          	 [2]
		        ],
	      
	      
	        "turn_II":[
				[2, 4],
        			[8, 10, 1],
	   			[3],
	          		[6]
			],
	      
	      
	        "turn_III": [
        	  		[6, 7],
				[9],
				[11, 12],
        			[4]
	       		 ],
	      
	      
	        "turn_IV":[
			        [3],
	         		[5, 8]
	       		 ]
	      
		  }

	},
 

		
	"score_card":{
			
  	"Team_A": {
		

   		"I": {
      			"defender": [1, 2, 3],
      			"attacker": [4, 5, 6],
      			"run_time": ["0:30", "0:45"],
      			"per_time": ["1:00"],
      			"symbol": "+"
    			},

   		 "II": {
    			 "defender": [7, 8, 9],
      			"attacker": [10, 11],
      			"run_time": ["0:20"],
     			"per_time": ["0:50"],
      			"symbol": "-"
    			}
  		},

	"Team_B": {
		

   		"I": {
      			"defender": [1, 2, 3],
      			"attacker": [4, 5, 6],
      			"run_time": ["0:30", "0:45"],
      			"per_time": ["1:00"],
      			"symbol": "+"
    			},

   		 "II": {
    			 "defender": [7, 8, 9],
      			"attacker": [10, 11],
      			"run_time": ["0:20"],
     			"per_time": ["0:50"],
      			"symbol": "-"
    			}
  		}
	},
	

	
  	"result": {
    		"team_a_total": 52,
    		"team_b_total": 47,
    		"won_by": "5 points",
    		"team_won": "Shivaji Warriors",

       		"team_A": {
     			 "I": ["3", "-"],
     			 "II": ["42", "-"],
      			"III": ["45", "-"],
     			 "IV": "-"
   		 },

		"team_B": {
			"I": ["3", "-"],
  			 "II": ["42", "-"],
  			 "III": ["45", "-"],
  			 "IV": "-"
    		}
 	 },

				
	"match_staff": {
   	 	"scorer_1": "Amit Patil",
   	 	"scorer_2": "Rohit Sharma",
    		"umpire_1": "Suresh Pawar",
    		"umpire_2": "Mahesh Jadhav",
    		"post_umpire_1": "Vikas Kale",
    		"post_umpire_2": "Nitin Shinde",
    		"dugout": "Team A Bench",
    		"timekeeper": "Anil More",
    		"referee": "Prakash Deshmukh"
  	}
   
  
	
}"""


try:
    print("Testing parser...")
    
    cleaned_body = re.sub(r';\s*$', ',', raw_body, flags=re.MULTILINE)
    cleaned_body = re.sub(r'\"id\"\s*:\s*\d+\s*;', lambda m: m.group(0).replace(';', ','), cleaned_body)
    cleaned_body = re.sub(r',\s*([\]}])', r'\1', cleaned_body)
    
    # Test loading
    res = json.loads(cleaned_body)
    print("KEYS LOADED:", res.keys())
    
except Exception as e:
    print(f"FAILED PARSING: {e}")
    # Show approx context around error
    if "line" in str(e) and "column" in str(e):
        import traceback
        lines = cleaned_body.split("\n")
        m = re.search(r'line (\d+)', str(e))
        if m:
            line_no = int(m.group(1))
            print("CONTEXT:")
            print("\n".join(lines[line_no-5:line_no+5]))
