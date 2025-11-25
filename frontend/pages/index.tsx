import { GetStaticProps } from "next";
import { useRouter } from "next/router";
import {
  Container,
  Title,
  Text,
  SimpleGrid,
  Card,
  Group,
  Badge,
  Stack,
  Center,
} from "@mantine/core";
import { IconMap, IconMapPin } from "@tabler/icons-react";
import { getCitiesServerSide, City } from "@/services/citiesApi";

interface HomeProps {
  cities: City[];
}

export default function Home({ cities }: HomeProps) {
  const router = useRouter();

  const handleCityClick = (cityName: string) => {
    router.push(`/city/${cityName}`);
  };

  return (
    <Container size="lg" py="xl">
      <Stack gap="xl">
        <Center>
          <Stack gap="md" align="center">
            <Group>
              <IconMap size={48} />
              <Title order={1}>Spatially Zoning</Title>
            </Group>
            <Text size="lg" c="dimmed" ta="center">
              Explore zoning regulations and chat with AI about city planning
            </Text>
          </Stack>
        </Center>

        <div>
          <Title order={2} mb="md">
            Select a City
          </Title>
          {cities.length === 0 ? (
            <Card withBorder p="xl">
              <Text c="dimmed" ta="center">
                No cities available. Please check your backend connection.
              </Text>
            </Card>
          ) : (
            <SimpleGrid
              cols={{ base: 1, sm: 2, md: 3 }}
              spacing="lg"
            >
              {cities.map((city) => (
                <Card
                  key={city.id}
                  shadow="sm"
                  padding="lg"
                  radius="md"
                  withBorder
                  style={{ cursor: "pointer" }}
                  onClick={() => handleCityClick(city.name)}
                  className="hover:shadow-lg transition-shadow"
                >
                  <Group justify="space-between" mb="xs">
                    <Text fw={500} tt="capitalize" size="lg">
                      {city.name}
                    </Text>
                    <IconMapPin size={20} />
                  </Group>
                  <Text size="sm" c="dimmed">
                    Click to explore zoning information and chat about
                    regulations
                  </Text>
                  <Badge color="blue" variant="light" mt="md">
                    View Map & Chat
                  </Badge>
                </Card>
              ))}
            </SimpleGrid>
          )}
        </div>
      </Stack>
    </Container>
  );
}

export const getStaticProps: GetStaticProps<HomeProps> = async () => {
  const { cities } = await getCitiesServerSide();

  return {
    props: {
      cities,
    },
    // Revalidate every hour (3600 seconds) to pick up new cities
    revalidate: 3600,
  };
};
