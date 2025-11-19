import { Image, Paper, Text } from "@mantine/core";

export interface CountryFlag {
  svgFlag: string;
  emojiFlag: string;
}

export const countryFlags = {
  UK: {
    svgFlag: "https://flagcdn.com/gb.svg",
    emojiFlag: "🇬🇧",
  },
  VN: {
    svgFlag: "https://flagcdn.com/vn.svg",
    emojiFlag: "🇻🇳",
  },
  US: {
    svgFlag: "https://flagcdn.com/us.svg",
    emojiFlag: "🇺🇸",
  },
  CA: {
    svgFlag: "https://flagcdn.com/ca.svg",
    emojiFlag: "🇨🇦",
  },
  BR: {
    svgFlag: "https://flagcdn.com/br.svg",
    emojiFlag: "🇧🇷",
  },
  ES: {
    svgFlag: "https://flagcdn.com/es.svg",
    emojiFlag: "🇪🇸",
  },
  IT: {
    svgFlag: "https://flagcdn.com/it.svg",
    emojiFlag: "🇮🇹",
  },
  NZ: {
    svgFlag: "https://flagcdn.com/nz.svg",
    emojiFlag: "🇳🇿",
  },
  MX: {
    svgFlag: "https://flagcdn.com/mx.svg",
    emojiFlag: "🇲🇽",
  },
  CN: {
    svgFlag: "https://flagcdn.com/cn.svg",
    emojiFlag: "🇨🇳",
  },
  AU: {
    svgFlag: "https://flagcdn.com/au.svg",
    emojiFlag: "🇦🇺",
  },
  JP: {
    svgFlag: "https://flagcdn.com/jp.svg",
    emojiFlag: "🇯🇵",
  },
  FR: {
    svgFlag: "https://flagcdn.com/fr.svg",
    emojiFlag: "🇫🇷",
  },
  DE: {
    svgFlag: "https://flagcdn.com/de.svg",
    emojiFlag: "🇩🇪",
  },
  IN: {
    svgFlag: "https://flagcdn.com/in.svg",
    emojiFlag: "🇮🇳",
  },
  CAM: {
    svgFlag: "https://flagcdn.com/kh.svg",
    emojiFlag: "🇰🇭",
  },
};

export const SVGCountryFlag = ({ flag }: { flag: CountryFlag }) => {
  return (
    <Paper shadow="xs" w={20} h={14}>
      <Image src={flag.svgFlag} w={20} h={14} fit="cover" />
    </Paper>
  );
};

export const EmojiCountryFlag = ({ flag }: { flag: CountryFlag }) => {
  return (
    <Text
      component="span"
      style={(theme) => ({ textShadow: theme.shadows.xs })}
    >
      {flag.emojiFlag}
    </Text>
  );
};

export const CountryFlagComponent = navigator.userAgent.includes("Windows")
  ? SVGCountryFlag
  : EmojiCountryFlag;
