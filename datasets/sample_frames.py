import pandas as pd
from datasets import load_dataset
import json
import os

def sample_frames():
    print("🚀 Loading google/frames-benchmark from HuggingFace...")
    ds = load_dataset("google/frames-benchmark", split="test")
    df = ds.to_pandas()
    
    print(f"📊 Total questions in dataset: {len(df)}")
    print(f"🔍 Reasoning types found: {df['reasoning_types'].unique()}")
    
    # We want 25 from each major reasoning type
    # Typical types in FRAMES: numerical, tabular, temporal, multiple constraints
    # Sometimes they are lists, so we normalize
    
    selected_indices = []
    # Note: Case sensitive in the dataset
    types_to_sample = ['Numerical reasoning', 'Tabular reasoning', 'Temporal reasoning', 'Multiple constraints']
    
    for r_type in types_to_sample:
        # Filter for rows that contains this reasoning type in the string
        type_df = df[df['reasoning_types'].str.contains(r_type, na=False)]
        
        sample_size = min(25, len(type_df))
        if sample_size > 0:
            sample = type_df.sample(n=sample_size, random_state=42)
            selected_indices.extend(sample.index.tolist())
            print(f"✅ Sampled {len(sample)} for type: {r_type}")
        else:
            print(f"⚠️ No samples found for type: {r_type}")

    # Remove duplicates
    selected_indices = list(set(selected_indices))

    # If we don't have enough, fill with others
    if len(selected_indices) < 100:
        remaining = 100 - len(selected_indices)
        others = df[~df.index.isin(selected_indices)]
        if len(others) >= remaining:
            fill = others.sample(n=remaining, random_state=42)
            selected_indices.extend(fill.index.tolist())
            print(f"➕ Filled {remaining} additional questions from other types.")

    final_df = df.loc[selected_indices].head(100)
    print(f"📊 Columns available: {final_df.columns.tolist()}")
    
    # Check for question column (it's often 'Prompt' or 'question' or 'input')
    q_col = 'Prompt' if 'Prompt' in final_df.columns else ('prompt' in final_df.columns if 'prompt' in final_df.columns else ('question' if 'question' in final_df.columns else 'input'))
    a_col = 'Answer' if 'Answer' in final_df.columns else 'answer'
    
    # Convert to a format compatible with our benchmark script
    output_data = []
    all_wiki_urls = set()
    for _, row in final_df.iterrows():
        gold_titles = []
        
        # Method 1: from 'wiki_links' if exists and populated
        if 'wiki_links' in row and row['wiki_links'] is not None and len(row['wiki_links']) > 0:
            for link in row['wiki_links']:
                if isinstance(link, dict):
                    gold_titles.append(link.get('title', ''))
                    if 'url' in link:
                        all_wiki_urls.add(link['url'])
        
        # Method 2: from wikipedia_link_1, wikipedia_link_2...
        if not gold_titles:
            for i in range(1, 12):
                col = f'wikipedia_link_{i}'
                if i == 11: col = 'wikipedia_link_11+'
                if col in row and row[col] is not None and isinstance(row[col], str) and row[col].strip():
                    url = row[col].strip()
                    all_wiki_urls.add(url)
                    # Extract title from URL (last part of wikipedia URL)
                    title = url.split('/')[-1].replace('_', ' ')
                    gold_titles.append(title)
        
        output_data.append({
            "id": row.get("id", str(_)),
            "question": row[q_col],
            "answer": str(row[a_col]),
            "gold_titles": list(set(gold_titles)),
            "reasoning_types": row["reasoning_types"]
        })
        
    os.makedirs("datasets", exist_ok=True)
    with open("datasets/frames_100.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    with open("datasets/frames_wiki_urls.txt", "w") as f:
        for url in sorted(list(all_wiki_urls)):
            f.write(f"{url}\n")
        
    print(f"🎉 Successfully saved 100 questions to datasets/frames_100.json")
    print(f"🔗 Saved {len(all_wiki_urls)} unique Wiki URLs to datasets/frames_wiki_urls.txt")

if __name__ == "__main__":
    sample_frames()
