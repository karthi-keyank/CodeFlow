from engine import PageTextExtractor

def main():
    extractor = PageTextExtractor()
    extractor.run("https://skillrack.com/")

if __name__ == "__main__":
    main()
