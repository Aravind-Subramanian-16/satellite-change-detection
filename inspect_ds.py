from datasets import load_dataset
import sys
import traceback

def main():
    try:
        ds = load_dataset("snchen1230/LEVIRCDPlus")
        print("Dataset loaded successfully!")
        print(ds)
        
        # Display sample features
        if 'train' in ds:
            print("\nTrain sample 0 features:")
            sample = ds['train'][0]
            print(sample.keys())
            for k in sample:
                if hasattr(sample[k], 'size'):
                    print(f"{k} size: {sample[k].size}")
    except Exception as e:
        print("Error:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
