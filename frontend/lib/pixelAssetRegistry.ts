export interface PixelAssetDefinition {
  key: string;
  label: string;
  src: string;
}

const notebookIconRegistry: Record<string, PixelAssetDefinition> = {
  atom: { key: "atom", label: "Atom", src: "/notebook-icons/atom.png" },
  balance_scale: { key: "balance_scale", label: "Balance Scale", src: "/notebook-icons/balance-scale.png" },
  brain: { key: "brain", label: "Brain", src: "/notebook-icons/brain.png" },
  calculator: { key: "calculator", label: "Calculator", src: "/notebook-icons/calculator.png" },
  chemical: { key: "chemical", label: "Chemical", src: "/notebook-icons/chemical.png" },
  computer: { key: "computer", label: "Computer", src: "/notebook-icons/computer.png" },
  dna: { key: "dna", label: "DNA", src: "/notebook-icons/dna.png" },
  fashion: { key: "fashion", label: "Fashion", src: "/notebook-icons/fashion.png" },
  finance: { key: "finance", label: "Finance", src: "/notebook-icons/finance.png" },
  function: { key: "function", label: "Function", src: "/notebook-icons/function.png" },
  hello_kitty: { key: "hello_kitty", label: "Hello Kitty", src: "/notebook-icons/hello-kitty.png" },
  info: { key: "info", label: "Info", src: "/notebook-icons/info.png" },
  law: { key: "law", label: "Law", src: "/notebook-icons/law.png" },
  mail: { key: "mail", label: "Mail", src: "/notebook-icons/mail.png" },
  money: { key: "money", label: "Money", src: "/notebook-icons/money.png" },
  pixel_cat: { key: "pixel_cat", label: "Pixel Cat", src: "/notebook-icons/pixel-cat.png" },
  pixel_heart: { key: "pixel_heart", label: "Pixel Heart", src: "/notebook-icons/pixel-heart.png" },
  pixels: { key: "pixels", label: "Pixels", src: "/notebook-icons/pixels.png" },
  pride: { key: "pride", label: "Pride", src: "/notebook-icons/pride.png" },
  profit: { key: "profit", label: "Profit", src: "/notebook-icons/profit.png" },
  rain: { key: "rain", label: "Rain", src: "/notebook-icons/rain.png" },
  react: { key: "react", label: "React", src: "/notebook-icons/react.png" },
  robot: { key: "robot", label: "Robot", src: "/notebook-icons/robot.png" },
  spring: { key: "spring", label: "Spring", src: "/notebook-icons/spring.png" },
  stock: { key: "stock", label: "Stock", src: "/notebook-icons/stock.png" },
  team: { key: "team", label: "Team", src: "/notebook-icons/team.png" },
  team_alt: { key: "team_alt", label: "Team Alt", src: "/notebook-icons/team-alt.png" },
  teddy_bear: { key: "teddy_bear", label: "Teddy Bear", src: "/notebook-icons/teddy-bear.png" },
};

const defaultPixelAsset: PixelAssetDefinition = notebookIconRegistry.pixel_heart;

const legacyAliases: Record<string, keyof typeof notebookIconRegistry> = {
  address_book: "mail",
  folder: "robot",
  book: "brain",
  leaf: "spring",
  badge: "pixel_heart",
  briefcase: "team",
  cell: "dna",
  chart: "stock",
  chip: "computer",
  coin: "money",
  connect: "team",
  gavel: "law",
  loss: "stock",
  musical_note: "fashion",
  pencil: "function",
  robotic: "robot",
  robots: "robot",
  tooth: "chemical",
};

export function getPixelAsset(assetKey?: string | null): PixelAssetDefinition {
  if (assetKey && notebookIconRegistry[assetKey]) {
    return notebookIconRegistry[assetKey];
  }

  if (assetKey && legacyAliases[assetKey]) {
    return notebookIconRegistry[legacyAliases[assetKey]] ?? defaultPixelAsset;
  }

  return defaultPixelAsset;
}

export const pixelIconOptions = Object.values(notebookIconRegistry);
export const studyPixelIconOptions = Object.values(notebookIconRegistry);
